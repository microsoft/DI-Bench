"""
This script is intended to collect repo data including instance
dict and repo cache from a repo_name list (raw_data/py_repo_list).
The next step is to curate the collected data with `mask.py`.

This script handles the pre-filtering process to skip the repos
without GitHub action workflows.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle
from pathlib import Path

from alive_progress import alive_bar
from fire import Fire
from github import Auth, Github

from bigbuild.utils.repo import clone_repo, fetch_metadata


def run_repo(
    repo_name: str,
    cache_dir: Path,
    output_jsonl: Path,
    language: str,
    token: str,
) -> None:
    auth = Auth.Token(token)
    g = Github(auth=auth)
    instance_id = repo_name.replace("/", "_")
    instance = {"instance_id": instance_id, "language": language}
    metadata = fetch_metadata(repo_name, g)
    instance["metadata"] = metadata
    repo_name = metadata["full_name"]
    if not os.path.exists(cache_dir / instance_id):
        clone_repo(repo_name, cache_dir / instance_id)
    with open(output_jsonl, "a") as f:
        f.write(json.dumps(instance) + "\n")


def main(
    repo_list_file: str,
    cache_dir: str,
    output_jsonl: str,
    language: str,
    tokens_file: str = ".cache/TOKENS",
    concurrency: int = 20,
):
    with open(repo_list_file, "r") as f:
        repo_list = f.readlines()

    with open(tokens_file, "r") as f:
        tokens = f.readlines()

    tokens = cycle(tokens)

    print(f"Total repos: {len(repo_list)}")
    cache_dir = Path(cache_dir)
    output_jsonl = Path(output_jsonl)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                run_repo,
                repo_name.strip(),
                Path(cache_dir),
                Path(output_jsonl),
                language,
                next(tokens).strip(),
            )
            for repo_name in repo_list
        ]
        with alive_bar(len(futures)) as bar:
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(e)
                bar()


if __name__ == "__main__":
    Fire(main)
