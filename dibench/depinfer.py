import asyncio
import functools
import glob
import json
import pathlib
import traceback

from rich.progress import Progress, TaskID
from tenacity import retry, stop_after_attempt, wait_random_exponential
from tree_sitter import Parser, Query
from tree_sitter_languages import get_language, get_parser

from dibench import RepoInstance
from dibench.prompt import (
    file_template,
    instruction,
    lazy_prompt,
    merge_build_files_instruction,
    merge_build_files_task,
    task_information_template,
)
from dibench.utils import cprint, progress
from dibench.utils.provider import BaseProvider, get_llm
from dibench.utils.repo import fake_git_diff, lang2suffix, show_project_structure

languages = ["python", "rust", "csharp", "javascript"]

tree_sitter_parsers = {
    "python": get_parser("python"),
    "rust": get_parser("rust"),
    "csharp": get_parser("c_sharp"),
    "javascript": get_parser("javascript"),
}

tree_sitter_languages = {
    "python": get_language("python"),
    "rust": get_language("rust"),
    "csharp": get_language("c_sharp"),
    "javascript": get_language("javascript"),
}

tree_sitter_queries = {
    "python": tree_sitter_languages["python"].query(
        "[(import_statement) (import_from_statement)] @import",
    ),
    "rust": tree_sitter_languages["rust"].query("(use_declaration) @use"),
    "csharp": tree_sitter_languages["csharp"].query("(using_directive) @use"),
    "javascript": tree_sitter_languages["javascript"].query(
        "(import_statement) @import"
    ),
}


def sanitize(response: str, instance: RepoInstance):
    """
    Processes a response string to extract and organize edits associated with
    build file listings. It identifies and refines the edits based on
    filename extraction from the response, prioritizing by filename source
    reliability. The function returns a dictionary of build files with their
    corresponding edited content.

    Args:
        response (str): The response containing potential build file listings
                        and edits.
        instance (RepoInstance): An instance containing information about the
                                 repository, including available build files.

    Returns:
        dict: A dictionary mapping each build file name to its corresponding
              edited content.
    """
    output = []
    lines = response.splitlines(keepends=True)
    edits = []
    saw_fname = None
    fname = None
    fname_source = None
    new_lines = []
    for i, line in enumerate(lines):
        if line.startswith("```") or line.startswith("```"):
            if fname is not None:
                # ending an existing block
                saw_fname = None
                edits.append((fname, fname_source, new_lines))
                fname = None
                fname_source = None
                new_lines = []
                continue

            # fname==None ... starting a new block
            if i > 0:
                fname_source = "block"
                fname = lines[i - 1].strip()
                fname = fname.strip("*")  # handle **filename.py**
                fname = fname.rstrip(":")
                fname = fname.strip("`")
                fname = fname.lstrip("#")
                fname = fname.strip()
                if len(fname) > 250:
                    fname = ""

                # Did gpt prepend a bogus dir? It especially likes to
                # include the path/to prefix from the one-shot example in
                # the prompt.
                if (
                    fname
                    and fname not in instance.build_files
                    and pathlib.Path(fname).name in instance.build_files
                ):
                    fname = pathlib.Path(fname).name
            if not fname:  # blank line? or ``` was on first line i==0
                if saw_fname:
                    fname = saw_fname
                    fname_source = "saw"
                elif len(instance.build_files) == 1:
                    fname = instance.build_files[0]
                    fname_source = "chat"
                else:
                    cprint("No filename provided before ``` in file listing", "red")
        elif fname is not None:
            new_lines.append(line)
        else:
            for word in line.strip().split():
                word = word.rstrip(".:,;!")
                for build_file in instance.build_files:
                    quoted_chat_file = f"`{build_file}`"
                    if word == quoted_chat_file:
                        saw_fname = build_file
            output.append(line)
    if fname:
        edits.append((fname, fname_source, new_lines))

    seen = set()
    refined_edits = []
    # process from most reliable filename, to least reliable
    for source in ("block", "saw", "chat"):
        for fname, fname_source, new_lines in edits:
            if fname_source != source:
                continue
            # if a higher priority source already edited the file, skip
            if fname in seen:
                continue

            seen.add(fname)
            refined_edits.append((fname, fname_source, new_lines))

    build_files = {}
    for build_file in instance.build_files:
        # find the build file with the highest probability
        for fname, fname_source, new_lines in refined_edits:
            if build_file in fname or pathlib.Path(fname).name == build_file:
                build_files[build_file] = "".join(new_lines)
                break
    return build_files


def original_build_files(instance: RepoInstance, project_root: pathlib.Path | None):
    return {file: (project_root / file).read_text() for file in instance.build_files}


def make_patch(
    new_build_files: dict[str, str],
    instance: RepoInstance,
    project_root: pathlib.Path | None,
):
    # get old build files
    old_build_files = original_build_files(instance, project_root)
    # if key is not in new_build_files, add it
    for file in old_build_files:
        if file not in new_build_files:
            new_build_files[file] = old_build_files[file]
            cprint(
                f"build file {file} is not in the new build files. Adding it from the original build files.",
                "yellow",
            )

    diff_pair = {
        file: (old_build_files[file], new_build_files[file])
        for file in new_build_files.keys()
    }

    patch = fake_git_diff("playground", diff_pair)
    return patch


def load_bigbuild_dataset(dataset_name_or_path: str) -> list[RepoInstance]:
    dataset = [
        json.loads(line)
        for line in pathlib.Path(dataset_name_or_path).read_text().splitlines()
    ]
    return [RepoInstance(**instance) for instance in dataset]


def import_statements(
    existing_src_content: str, content: str, ts_parser: Parser, query: Query
) -> str:
    dep_related_statements = []
    content: bytes = content.encode()
    tree = ts_parser.parse(content)
    for node, _ in query.captures(tree.root_node):
        dep_related_statements.append(content[node.start_byte : node.end_byte].decode())
    if len(dep_related_statements) == 0:
        return None
    ret = "..."
    for s in dep_related_statements:
        # if statement is already existing
        if s in existing_src_content:
            continue
        ret += f"\n{s}"
        ret += "\n..."
    return ret


def all_src_files(root: pathlib.Path, lang_suffix: list[str]) -> list[str]:
    files_to_include = []
    for suffix in lang_suffix:
        for file in glob.glob(f"{root}/**/*{suffix}", recursive=True):
            file = str(pathlib.Path(file).relative_to(root))
            # exclude setup.py
            if file == "setup.py":
                continue
            files_to_include.append(file)
    return files_to_include


def md_dumps_messages(messages: list[dict]) -> str:
    """Dump messages into markdown format"""
    md_history = ""
    for message in messages:
        md_history += f"## {message['role'].capitalize()}\n{message['content']}\n\n"
    return md_history


@retry(wait=wait_random_exponential(max=100), stop=stop_after_attempt(10))
async def query_llm(
    llm: BaseProvider,
    messages: list[str],
    max_new_tokens: int = 1024,
    temperature: float = 0.0,
    n: int = 1,
):
    try:
        return await llm.generate_reply(messages, max_new_tokens, temperature, n)
    except Exception as e:
        raise e


def make_prompt(
    instance: RepoInstance,
    project_root: pathlib.Path | None,
    src_files: list[str] | None = None,
    import_only: bool = False,
) -> list[dict]:
    project_structure = show_project_structure(
        project_root, exclude_dirs=[".git", ".github"]
    )
    # src_files = src_files(project_root, lang2suffix[instance.language.lower()])
    if import_only:
        ts_parser = tree_sitter_parsers[instance.language.lower()]
        ts_query = tree_sitter_queries[instance.language.lower()]
        src_section = ""
        for file in src_files:
            retrieved = import_statements(
                src_section, (project_root / file).read_text(), ts_parser, ts_query
            )
            if not retrieved:
                continue
            src_section += "\n" + file_template.format(path=file, content=retrieved)
    else:
        src_section = "\n".join(
            file_template.format(path=file, content=(project_root / file).read_text())
            for file in src_files
        )

    env_specs = "\n".join(f"- {k}: {v}" for k, v in instance.env_specs.items())
    build_section = "\n".join(
        file_template.format(path=file, content=(project_root / file).read_text())
        for file in instance.build_files
    )
    task = task_information_template.format(
        project_structure=project_structure,
        env_specs=env_specs,
        src_section=src_section,
        build_section=build_section,
    )
    prompt = instruction + "\n" + task + "\n" + instruction + "\n" + lazy_prompt
    return [
        {
            "role": "system",
            "content": f"You are a senior expert in {instance.language.lower()}",
        },
        {"role": "user", "content": prompt},
    ]


def async_exception_handler(coroutine):
    @functools.wraps(coroutine)
    async def wrapper(**kwargs):
        try:
            return await coroutine(**kwargs)
        except Exception as e:
            cprint(
                f"An exception occurred: {e} for {kwargs['instance'].instance_id}",
                "red",
            )
            cprint(f"Error log is saved at {kwargs['workspace'] / 'error.log'}", "red")
            with open(kwargs["workspace"] / "error.log", "w") as f:
                f.write(traceback.format_exc())
            kwargs["progress"].update(kwargs["task_id"], advance=1)
            return {
                "instance_id": kwargs["instance"].instance_id,
                "patch": None,
            }

    return wrapper


@async_exception_handler
async def all_in_one_infer(
    *,
    llm: BaseProvider,
    instance: RepoInstance,
    project_root: pathlib.Path,
    workspace: pathlib.Path,
    progress: Progress,
    task_id: TaskID,
):
    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
    else:
        assert workspace.is_dir(), f"{workspace} is not a directory"
    if (workspace / "patch.diff").exists():
        cprint(f"Patch for {instance.instance_id} is already generated", "yellow")
        progress.update(task_id, advance=1)
        return {
            "instance_id": instance.instance_id,
            "patch": (workspace / "patch.diff").read_text(),
        }
    src_files = all_src_files(project_root, lang2suffix[instance.language.lower()])
    messages = make_prompt(instance, project_root, src_files, import_only=False)
    # sync query
    response = await query_llm(
        llm=llm,
        messages=messages,
        max_new_tokens=4096,
        temperature=0.0,
        n=1,
    )
    messages.append({"role": "assistant", "content": response})
    md_history = md_dumps_messages(messages)
    with (workspace / "build.md").open("w") as f:
        f.write(md_history)
    trajs = json.dumps(messages)
    with (workspace / "trajs.json").open("w") as f:
        f.write(trajs)
    patch = make_patch(sanitize(response, instance), instance, project_root)
    with (workspace / "patch.diff").open("w") as f:
        f.write(patch)
    progress.update(task_id, advance=1)
    cprint(
        f"Patch for {instance.instance_id} is saved at {workspace / 'patch.diff'}",
        "green",
    )
    return {"instance_id": instance.instance_id, "patch": patch}


@async_exception_handler
async def import_only_infer(
    *,
    llm: BaseProvider,
    instance: RepoInstance,
    project_root: pathlib.Path,
    workspace: pathlib.Path,
    progress: Progress,
    task_id: TaskID,
):
    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
    else:
        assert workspace.is_dir(), f"{workspace} is not a directory"
    if (workspace / "patch.diff").exists():
        cprint(f"Patch for {instance.instance_id} is already generated", "yellow")
        progress.update(task_id, advance=1)
        return {
            "instance_id": instance.instance_id,
            "patch": (workspace / "patch.diff").read_text(),
        }
    src_files = all_src_files(project_root, lang2suffix[instance.language.lower()])
    messages = make_prompt(instance, project_root, src_files, import_only=True)
    response = await query_llm(
        llm=llm,
        messages=messages,
        max_new_tokens=4096,
        temperature=0.0,
        n=1,
    )
    messages.append({"role": "assistant", "content": response})
    md_history = md_dumps_messages(messages)
    with (workspace / "build.md").open("w") as f:
        f.write(md_history)
    trajs = json.dumps(messages)
    with (workspace / "trajs.json").open("w") as f:
        f.write(trajs)
    patch = make_patch(sanitize(response, instance), instance, project_root)
    with (workspace / "patch.diff").open("w") as f:
        f.write(patch)
    progress.update(task_id, advance=1)
    cprint(
        f"Patch for {instance.instance_id} is saved at {workspace / 'patch.diff'}",
        "green",
    )
    return {"instance_id": instance.instance_id, "patch": patch}


@async_exception_handler
async def file_iter_infer(
    *,
    llm: BaseProvider,
    instance: RepoInstance,
    project_root: pathlib.Path,
    workspace: pathlib.Path,
    progress: Progress,
    task_id: TaskID,
):
    # for efficiency
    instruction_ = instruction.replace(
        "1. The project may include multiple build files. Ensure you update all of them with the necessary dependency configurations.",
        "1. The project may include multiple build files. You can only edit some of them with the necessary dependency configurations.",
    )

    instruction_ = instruction_.replace(
        "3. **Source Code**: The full source code of the project.",
        "3. **Source Code**: One source code file of the project.",
    )
    if not workspace.exists():
        workspace.mkdir(parents=True, exist_ok=True)
    else:
        assert workspace.is_dir(), f"{workspace} is not a directory"
    if (workspace / "patch.diff").exists():
        cprint(f"Patch for {instance.instance_id} is already generated", "yellow")
        progress.update(task_id, advance=1)
        return {
            "instance_id": instance.instance_id,
            "patch": (workspace / "patch.diff").read_text(),
        }
    src_files = all_src_files(project_root, lang2suffix[instance.language.lower()])
    all_messages = []
    responses = []
    for file in src_files:
        messages = make_prompt(instance, project_root, [file], import_only=False)
        try:
            response = await query_llm(
                llm=llm,
                messages=messages,
                max_new_tokens=4096,
                temperature=0.0,
                n=1,
            )
            messages.append({"role": "assistant", "content": response})
            all_messages.extend(messages)
            responses.append(response)
        except Exception as e:
            cprint(e, "red")
    proposed_edits = []
    for response in responses:
        proposed_edits.append(sanitize(response, instance))

    project_structure = show_project_structure(
        project_root, exclude_dirs=[".git", ".github"]
    )
    final_edits = {}
    for file in instance.build_files:
        origin_content = (project_root / file).read_text()
        build_section_for_current_file = file_template.format(
            path=file, content=origin_content
        )
        edits_for_current_file = []
        for proposed_edit in proposed_edits:
            if file not in proposed_edit or proposed_edit[file] == origin_content:
                continue
            edits_for_current_file.append(
                file_template.format(path=file, content=proposed_edit[file])
            )

        task = merge_build_files_task.format(
            project_structure=project_structure,
            env_specs="\n".join(f"- {k}: {v}" for k, v in instance.env_specs.items()),
            build_file_edits="\n".join(edits_for_current_file),
            build_section=build_section_for_current_file,
        )
        prompt = (
            merge_build_files_instruction
            + "\n"
            + task
            + "\n"
            + merge_build_files_instruction
            + "\n"
            + lazy_prompt
        )
        messages = [
            {
                "role": "system",
                "content": f"You are a senior expert in {instance.language.lower()}",
            },
            {"role": "user", "content": prompt},
        ]
        try:
            response = await query_llm(
                llm=llm,
                messages=messages,
                max_new_tokens=4096,
                temperature=0.0,
                n=1,
            )
            messages.append({"role": "assistant", "content": response})
            all_messages.extend(messages)
            new_build_content = sanitize(response, instance)
            if file not in new_build_content:
                cprint("No new content for the build file", "yellow")
            else:
                final_edits[file] = new_build_content[file]
        except Exception as e:
            cprint(e, "red")

    md_history = md_dumps_messages(all_messages)
    with (workspace / "build.md").open("w") as f:
        f.write(md_history)
    trajs = json.dumps(messages)
    with (workspace / "trajs.json").open("w") as f:
        f.write(trajs)
    patch = make_patch(final_edits, instance, project_root)
    with (workspace / "patch.diff").open("w") as f:
        f.write(patch)
    progress.update(task_id, advance=1)
    cprint(
        f"Patch for {instance.instance_id} is saved at {workspace / 'patch.diff'}",
        "green",
    )
    return {"instance_id": instance.instance_id, "patch": patch}


infer_method = {
    "all-in-one": all_in_one_infer,
    "import-only": import_only_infer,
    "file-iter": file_iter_infer,
}


def main(
    model: str = "gpt-4",
    method: str = "all-in-one",
    results_dir: str = "results/",
    workspace: str = "workspace/",
    dataset_name_or_path: str = "repo-regular.jsonl",
    repo_instances_dir: str | None = None,
):
    dataset = load_bigbuild_dataset(dataset_name_or_path)
    result_path = pathlib.Path(results_dir) / f"{method}-{model}.jsonl"
    workspace_path = pathlib.Path(workspace) / f"{method}-{model}"
    if not result_path.parent.exists():
        result_path.parent.mkdir(parents=True)
    if not workspace_path.exists():
        workspace_path.mkdir(parents=True)
    llm = get_llm(model, use_async=True)
    results = []
    tasks = []
    with progress("DepInfer") as p:
        tasks = []
        task_id = p.add_task("DepInfer", total=len(dataset))
        for instance in dataset:
            workspace = (
                workspace_path / instance.language.lower() / instance.instance_id
            )
            project_root = (
                pathlib.Path(repo_instances_dir)
                / instance.language.lower()
                / instance.instance_id
            )
            tasks.append(
                infer_method[method](
                    llm=llm,
                    instance=instance,
                    project_root=project_root,
                    workspace=workspace,
                    progress=p,
                    task_id=task_id,
                )
            )
        loop = asyncio.get_event_loop()
        coros = asyncio.gather(*tasks)
        results = loop.run_until_complete(coros)
    with result_path.open("w") as f:
        json.dump(results, f, indent=2)


if __name__ == "__main__":
    from fire import Fire

    Fire(main)
