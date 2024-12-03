import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

from alive_progress import alive_bar
from fire import Fire


def clone_and_checkout(
    url: str,
    sha: str,
    dst: str,
):
    if os.path.exists(dst):
        shutil.rmtree(dst)

    subprocess.run(
        ["git", "clone", url, dst],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    subprocess.run(
        ["git", "reset", "--hard", sha],
        check=True,
        cwd=dst,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main(
    jsonl: str,
    folder: str,
):
    with open(jsonl, "r") as f:
        instances = [json.loads(line) for line in f]

    with alive_bar(len(instances)) as bar:
        with ThreadPoolExecutor() as executor:
            futures = []
            for instance in instances:
                url = instance["metadata"]["html_url"]
                url = f"{url}.git"
                sha = instance["metadata"]["commit_sha"]
                instance_id = instance["instance_id"]
                dst = os.path.join(folder, instance_id)
                future = executor.submit(clone_and_checkout, url, sha, dst)
                futures.append(future)

            for future in as_completed(futures):
                future.result()
                bar()


if __name__ == "__main__":
    Fire(main)
