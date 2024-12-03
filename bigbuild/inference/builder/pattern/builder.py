from pathlib import Path

from tree_sitter_languages import get_language, get_parser

from bigbuild.utils.repo import lang2suffix, show_project_structure

from ..slide.builder import SlideBuilder, all_src_files
from ..slide.prompt import (
    file_content_template,
    instruction_template,
    system_prompt_template,
)

# this pattern is used to extract statesments like `import ...` from the source code
tree_sitter_queries = {
    "python": "[(import_statement) (import_from_statement)] @import",
    "rust": "(use_declaration) @use",
    "csharp": "(using_directive) @use",
    "typescript": "[(import_statement)  (import_require_clause)] @import",
}


class PatternBuilder(SlideBuilder):
    def __init__(
        self,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.ts_language = get_language(self.repo.language.lower())
        self.ts_parser = get_parser(self.repo.language.lower())
        self.query = self.ts_language.query(
            tree_sitter_queries[self.repo.language.lower()]
        )

    def _dep_related_content(self, content: str):
        dep_related_statementes = []
        content: bytes = content.encode()
        tree = self.ts_parser.parse(content)
        for node, _ in self.query.captures(tree.root_node):
            dep_related_statementes.append(
                content[node.start_byte : node.end_byte].decode()
            )
        if len(dep_related_statementes) == 0:
            return None
        ret = "..."
        for s in dep_related_statementes:
            ret += f"\n{s}"
            ret += "\n..."
        return ret

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
        dep_related_content = {}
        for file in src_files:
            related_content = self._dep_related_content((root / file).read_text())
            if related_content:
                dep_related_content[file] = related_content
        code_section = ""
        for file, content in dep_related_content.items():
            code_section += (
                file_content_template.format(
                    path=file, language=self.repo.language.lower(), content=content
                )
                + "\n"
            )
        yield system_prompt, self._current_prompt(
            instruction, project_structure, env_specs, code_section
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
