import json
import os
import shutil
from pathlib import Path
from typing import Tuple

from alive_progress import alive_bar
from dibench.curate.curator import make_curator
from fire import Fire


def run_instance(
    instance: dict,
    raw_path: Path,
    instance_path: Path,
    run_id: str,
) -> Tuple[bool, dict]:
    try:
        if not raw_path.exists():
            raise Exception(f"Project path {raw_path} does not exist")

        if instance_path.exists():
            shutil.rmtree(instance_path)
        shutil.copytree(raw_path, instance_path, symlinks=True)

        curator = make_curator(instance, instance_path, run_id)
        result = curator.to_mask()
        curator.export()
        return True, result
    except Exception as e:
        print(instance["instance_id"], e)
        return False, None


def main(
    input_jsonl: str,
    raw_dir: str,
    instance_dir: str,
    output_jsonl: str,
    run_id: str = None,
):
    """
    Run the curation process on a set of instances

    Args:
        input_jsonl (str): Path to the input jsonl file (obtained from the crawling step)
        raw_dir (str): Path to the directory containing the raw repo clones
        instance_dir (str): Path to the directory where the curated instances will be stored
        output_jsonl (str): Path to the output jsonl file
        run_id (str, optional): Run ID. Defaults to None.
    """
    with open(input_jsonl, "r") as f:
        instances = [json.loads(line) for line in f]
    print(f"Found {len(instances)} instances")
    os.makedirs(instance_dir, exist_ok=True)

    with alive_bar(len(instances)) as bar:
        for instance in instances:
            instance_id = instance["instance_id"]
            raw_path = Path(raw_dir) / instance_id
            instance_path = Path(instance_dir) / instance_id

            flag, result = run_instance(instance, raw_path, instance_path, run_id)
            if flag:
                with open(output_jsonl, "a") as f:
                    f.write(json.dumps(result) + "\n")
            bar()


if __name__ == "__main__":
    Fire(main)
