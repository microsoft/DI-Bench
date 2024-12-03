import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from alive_progress import alive_bar
from fire import Fire

from bigbuild.utils import load_bigbuild_dataset
from bigbuild.utils.repo import get_repo


def main(
    dataset_name_or_path="BigBuildBench/BigBuildBench",
    concurrency: int = 1,
):
    """
    B3 dataset download helper script.
    Args:
        dataset_name_or_path: dataset from huggingface or disk
        concurrency: num workers
    """
    dataset = load_bigbuild_dataset(dataset_name_or_path)
    cache_dir = Path(os.getenv("CACHE_DIR", ".cache"))
    repo_cache = cache_dir / "repo"

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(
                get_repo,
                instance,
                repo_cache / instance.instance_id,
            )
            for instance in dataset
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
