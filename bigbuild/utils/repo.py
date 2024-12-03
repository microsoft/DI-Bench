"""
This module contains utility functions for interacting with GitHub repositories.
"""

import os
import shutil
import subprocess
import uuid
from pathlib import Path

from github import Github

from bigbuild import RepoInstance

__all__ = [
    "get_repo",
    "fetch_metadata",
    "fake_git_diff",
    "fake_git_apply",
    "lang2suffix",
    "make_task_id",
]


def clone_repo(repo_name: str, dst: Path, timeout: int = 60) -> None:
    if dst.exists() and list(dst.iterdir()):
        return

    git_url = f"https://github.com/{repo_name}.git"

    try:
        subprocess.run(
            ["git", "clone", git_url, str(dst)],
            check=True,
            timeout=timeout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        raise Exception(f"Failed to clone {git_url}") from e


def get_repo(instance: RepoInstance, dst: Path, timeout: int = 120) -> None:
    """
    Get B3 repo instance.
    """
    # exist and not empty except .git
    if dst.exists():
        child_list = list(str(p.relative_to(dst)) for p in dst.iterdir())
        child_list = list(filter(lambda x: not x.startswith("."), child_list))
        if child_list:
            return
        shutil.rmtree(dst)

    ORG_NAME = "BigBuildBench"
    # git_url = f"https://github.com/{ORG_NAME}/{instance_id}.git"
    # TODO: change to http-based clone when public
    git_url = f"git@github.com:{ORG_NAME}/{instance.instance_id}.git"

    # print(f"Cloning {git_url} to {dst}")
    result = subprocess.run(
        ["git", "clone", git_url, str(dst)],
        timeout=timeout,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise Exception(f"Failed to clone {git_url}")

    # get the first commit message
    result = subprocess.run(
        ["git", "log", "--pretty=format:%s", "-n", "1"],
        cwd=dst,
        timeout=timeout,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise Exception(f"Failed to get commit {git_url}")

    commit_message = result.stdout.strip()
    if commit_message != "init instance":
        raise Exception(f">>>>> Not init: {instance.instance_id}")

    if result.returncode != 0:
        raise Exception(f"Failed to clone {git_url}")


def fetch_metadata(repo_name: str, g: Github) -> dict:
    """
    Get latest commit sha from default branch.
    """
    repo = g.get_repo(repo_name)
    latest_commit = repo.get_commits()[0]
    return {
        "name": repo.name,
        "repo_name": repo_name,
        "full_name": repo_name,
        "html_url": repo.html_url,
        "description": repo.description,
        "stargazers_count": repo.stargazers_count,
        "default_branch": repo.default_branch,
        "language": repo.language,
        "topics": repo.get_topics(),
        "pushed_at": repo.pushed_at.isoformat(),
        "created_at": repo.created_at.isoformat(),
        "updated_at": repo.updated_at.isoformat(),
        "commit_sha": latest_commit.sha[:7],
    }


def fake_git_diff(repo_playground: str, content: dict[str, tuple]):
    """create a fake git repo to obtain git diff format"""

    # Generate a temperary folder and add uuid to avoid collision
    repo_playground = os.path.join(repo_playground, str(uuid.uuid4()))

    # assert playground doesn't exist
    assert not os.path.exists(repo_playground), f"{repo_playground} already exists"

    # create playground
    os.makedirs(repo_playground)

    # create a fake git repo
    subprocess.run(f"cd {repo_playground} && git init", shell=True, capture_output=True)

    # create a file
    for file_path, (old_content, new_content) in content.items():
        subprocess.run(
            f"mkdir -p {repo_playground}/{os.path.dirname(file_path)}",
            shell=True,
            capture_output=True,
        )
        with open(f"{repo_playground}/{file_path}", "w") as f:
            f.write(old_content)
        # add file to git
        subprocess.run(
            f"cd {repo_playground} && git add {file_path} && git commit -m 'initial commit'",
            capture_output=True,
            shell=True,
        )
        # edit file
        with open(f"{repo_playground}/{file_path}", "w") as f:
            f.write(new_content)
    # get git diff
    o = subprocess.run(
        f"cd {repo_playground} && git diff", shell=True, capture_output=True
    )

    s = o.stdout.decode("utf-8")

    # remove playground
    subprocess.run(f"rm -rf {repo_playground}", shell=True)

    return s


def fake_git_apply(repo_playground: str, content: dict[str, str], patch: str) -> str:
    """create a fake git repo to apply diff and get patched content"""

    # Generate a temperary folder and add uuid to avoid collision
    repo_playground = os.path.join(repo_playground, str(uuid.uuid4()))

    # assert playground doesn't exist
    assert not os.path.exists(repo_playground), f"{repo_playground} already exists"

    # create playground
    os.makedirs(repo_playground)

    # create a fake git repo
    subprocess.run(f"cd {repo_playground} && git init", shell=True)

    for file_path, old_content in content.items():
        # create a file
        subprocess.run(
            f"mkdir -p {repo_playground}/{os.path.dirname(file_path)}", shell=True
        )

        with open(f"{repo_playground}/{file_path}", "w") as f:
            f.write(old_content)

    patch_file = f"{repo_playground}/patch.diff"
    with open(patch_file, "w") as f:
        f.write(patch)

    # patch_file = patch_file.relative_to(testbed)
    result = subprocess.run(
        f"cd {repo_playground} && git apply --allow-empty -v patch.diff",
        text=True,
        shell=True,
    )
    if result.returncode != 0:
        result = subprocess.run(
            f"cd {repo_playground} && patch --batch --fuzz=5 -p1 -i patch.diff",
            text=True,
            shell=True,
        )
        if result.returncode != 0:
            # remove playground
            subprocess.run(f"rm -rf {repo_playground}", shell=True)
            return None
    # remove playground
    new_content = {}
    for file_path in content.keys():
        file_content = Path(f"{repo_playground}/{file_path}").read_text()
        new_content[file_path] = file_content
    subprocess.run(f"rm -rf {repo_playground}", shell=True)
    return new_content


lang2suffix = {
    "python": [".py"],
    "go": [".go"],
    "cpp": [".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx", ".c", ".h"],
    "java": [".java"],
    "typescript": [".ts", ".js"],
    "javascript": [".ts", ".js"],
    "php": [".php"],
    "rust": [".rs"],
    "csharp": [".cs", ".csproj"],
}

lang2comment_prefix = {
    "python": "#",
    "java": "//",
    "typescript": "//",
    "rust": "//",
    "cpp": "//",
    "csharp": "//",
}


def make_task_id(instance_id: str, src_file: str) -> str:
    return f"{instance_id}-{src_file}"


def show_project_structure(
    root: Path, space: int = 0, exclude_dirs: list[str] = [".git", ".github"]
) -> str:
    """Show project structure with indentation.
    :param root: Path to the root directory.
    :param file_suffix: List of file suffixes to include.
    :param space: Number of spaces for indentation.
    :return: Project structure string.
    """
    if root.is_dir():
        structure = " " * space + f"{root.name}/\n"
    else:
        return " " * space + f"{root.name}\n"
    for item in root.iterdir():
        if item.name in exclude_dirs or item.name.startswith("."):
            continue
        structure += show_project_structure(item, space + 2, exclude_dirs)
    return structure
