import glob
import json
import re
from collections import OrderedDict
from pathlib import Path

from bigbuild.utils.build_system import make_build_system
from bigbuild.utils.llm.provider import make_provider
from bigbuild.utils.repo import fake_git_diff, lang2suffix, show_project_structure

from ..base import Builder, Repo
from .prompt import (
    file_content_template,
    instruction_template,
    prompt_template,
    system_prompt_template,
)


def make_patch(
    old_build_file_content: dict[str, str], new_build_file_content: dict[str, str]
) -> str:
    """
    generate a patch file from old_build_file_content to new_build_file_content
    """
    new_build_file_content_aligned = {}
    for file in old_build_file_content:
        if file in new_build_file_content:
            new_build_file_content_aligned[file] = new_build_file_content[file]
        else:
            # if not generated, keep the old content
            new_build_file_content_aligned[file] = old_build_file_content[file]
    return fake_git_diff(
        "playground",
        {
            file: (old_build_file_content[file], new_build_file_content_aligned[file])
            for file in old_build_file_content.keys()
        },
    )


def extract_new_build_file_content(raw_response: str, language: str) -> dict[str, str]:
    """
    each build file follows the format:
    file: <file_name>
    ```<language>
    <content>
    ```
    parse into a dictionary of file: content
    """
    build_file_content = OrderedDict()
    for match in re.finditer(
        r"file: (.+?)\n```" + language + r"\n(.*?)\n```", raw_response, re.DOTALL
    ):
        file_name, content = match.groups()
        build_file_content[file_name] = content
    return build_file_content


def all_src_files(root: Path, lang_suffix: list[str]) -> list[str]:
    files_to_include = []
    for suffix in lang_suffix:
        for file in glob.glob(f"{root}/**/*{suffix}", recursive=True):
            file = str(Path(file).relative_to(root))
            # exclude setup.py
            if file == "setup.py":
                continue
            files_to_include.append(file)
    return files_to_include


def identify_build_language(language, build_file) -> str:
    if language == "python":
        if ".toml" in build_file:
            return "toml"
        elif ".py" in build_file:
            return "python"
        elif ".txt" in build_file or ".pip" in build_file:
            return "txt"
        elif ".cfg" in build_file:
            return "cfg"
        else:
            print(f"Unknown build file for python: {build_file}")
            raise NotImplementedError(f"Unknown build file for python: {build_file}")
    elif language == "csharp":
        return "xml"
    elif language == "rust":
        return "toml"
    elif language == "typescript" or language == "javascript":
        return "json"
    print(f"Unknown build file for python: {build_file}")
    raise NotImplementedError(f"Build language for {language} is not implemented yet")


class SlideBuilder(Builder):
    def __init__(
        self,
        repo: Repo,
        model_name: str = "gpt-4o-20240806",
        backend: str = "azure",
        cache_dir: Path = Path(".cache/build"),
        resume: bool = True,
        max_seq_len: int = 1024 * 120,
        max_new_tokens: int = 1024 * 8,
        check_context: bool = False,
        base_url: str | None = None,
        tensor_parallel_size: int = 1,
        trust_remote_code: bool = False,
        attn_implementation=None,
    ):
        super().__init__(repo)
        self.repo = repo
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.use_cache = resume
        self.trajs = []
        self.max_seq_len = max_seq_len
        self.max_new_tokens = max_new_tokens
        self.check_context = check_context

        self.build_system = make_build_system(
            self.repo.language.lower(), self.repo.root, self.repo.build_files
        )
        self.build_content = {
            build_file: (Path(repo.root) / build_file).read_text()
            for build_file in repo.build_files
        }
        assert (
            len(self.repo.build_files) > 0
        ), f"No build file found in the repository {self.repo.name}, {self.repo}"
        assert list(self.build_content.keys()) == list(
            self.repo.build_files
        ), f"build files mismatch: {self.build_content.keys()} != {self.repo.build_files} for {self.repo.name}"

        self.build_lang = identify_build_language(
            self.repo.language.lower(), self.repo.build_files[0]
        )
        self.engine = make_provider(
            model_name,
            backend,
            base_url,
            tensor_parallel_size,
            max_seq_len,
            trust_remote_code,
            attn_implementation,
        )

    def _current_prompt(
        self,
        instruction: str,
        project_structure: str,
        env_specs: str,
        code_section: str,
    ):
        build_files = ""
        for file, content in self.build_content.items():
            build_files += file_content_template.format(
                path=file, language=self.build_system.language, content=content
            )
        prompt = prompt_template.format(
            instruction=instruction,
            project_structure=project_structure,
            env_specs=env_specs,
            code_section=code_section,
            build_files=build_files,
        )
        return prompt

    def _current_context_length(
        self,
        instruction: str,
        project_structure: str,
        env_specs: str,
        code_section: str,
    ) -> int:
        return self.engine.count_tokens(
            self._current_prompt(
                instruction, project_structure, env_specs, code_section
            )
        )

    def make_prompt(self):

        system_prompt = system_prompt_template.format(
            language=self.repo.language.lower()
        )
        instruction = instruction_template.format(
            language=self.build_system.language, example=self.build_system.example
        )
        root = Path(self.repo.root)
        project_structure = show_project_structure(
            root, exclude_dirs=[".git", ".github"]
        )
        src_files = all_src_files(root, lang2suffix[self.repo.language.lower()])
        env_specs = "\n".join(f"- {k}: {v}" for k, v in self.repo.env_specs.items())
        non_read_src_files = [
            (
                file,
                file_content_template.format(
                    path=file,
                    language=self.repo.language.lower(),
                    content=(root / file).read_text(),
                ),
            )
            for file in src_files
            if (root / file).is_file()
        ]
        if not self.check_context:
            yield system_prompt, self._current_prompt(
                instruction,
                project_structure,
                env_specs,
                "\n".join([content for _, content in non_read_src_files]),
            )
            return
        cur_code_section = ""
        while non_read_src_files:
            _, cur_file_content = non_read_src_files.pop(0)
            # TODO: edge case: cur_file_content is too long
            if (
                self._current_context_length(
                    instruction,
                    project_structure,
                    env_specs,
                    cur_code_section + "\n" + cur_file_content,
                )
                < self.max_seq_len - self.max_new_tokens - 1024
            ):  # 1024 as buffer
                cur_code_section += "\n" + cur_file_content
                continue
            yield system_prompt, self._current_prompt(
                instruction, project_structure, env_specs, cur_code_section
            )
            cur_code_section = cur_file_content
        yield system_prompt, self._current_prompt(
            instruction, project_structure, env_specs, cur_code_section
        )

    def dump_markdown(self):
        md_file = self.cache_dir / "build.md"
        content = f"# {self.repo.name}\n{self.repo}\n"
        for conversation in self.trajs:
            if conversation["role"] == "system":
                content += f"## System\n{conversation['content']}\n"
            elif conversation["role"] == "user":
                content += f"## User\n{conversation['content']}\n"
            elif conversation["role"] == "assistant":
                content += f"## Assistant\n{conversation['content']}\n"
        content += "## Errors\n" + "\n".join(self.errors)
        md_file.write_text(content)

    def patchgen(self) -> str | None:
        if self.use_cache and (self.cache_dir / "patch.diff").exists():
            return (self.cache_dir / "patch.diff").read_text()
        old_build_content = self.build_content.copy()
        self.errors = []
        for system_prompt, prompt in self.make_prompt():
            self.trajs.append({"role": "system", "content": system_prompt})
            self.trajs.append({"role": "user", "content": prompt})
            raw_response = self.engine.generate_reply(
                prompt, system_msg=system_prompt, max_tokens=self.max_new_tokens
            )[0]
            self.trajs.append(
                {"role": "assistant", "content": raw_response, "purpose": "build"},
            )
            new_build_content = extract_new_build_file_content(
                raw_response, self.build_lang
            )
            for file, content in new_build_content.items():
                if file not in self.build_content:
                    self.errors.append(
                        f"\nWarning[{self.repo.name}]: edited file({file}) not in build files"
                    )
                    print(self.errors[-1])
                    continue
                self.build_content[file] = content
        (self.cache_dir / "trajs.json").write_text(json.dumps(self.trajs))
        self.dump_markdown()
        # patch gen
        patch = make_patch(old_build_content, self.build_content)
        (self.cache_dir / "patch.diff").write_text(patch)
        return patch
