import json
import os
from os import PathLike
from pathlib import Path
from typing import cast

from datasets import Dataset, load_dataset

from bigbuild import RepoInstance


def load_bigbuild_dataset(
    dataset_name_or_path: str, split="test"
) -> list[RepoInstance]:
    if dataset_name_or_path.endswith(".json"):
        dataset = json.loads(Path(dataset_name_or_path).read_text())
    elif dataset_name_or_path.endswith(".jsonl"):
        dataset = [
            json.loads(line)
            for line in Path(dataset_name_or_path).read_text().splitlines()
        ]
    else:
        dataset = cast(Dataset, load_dataset(dataset_name_or_path, split=split))
    return [RepoInstance(**instance) for instance in dataset]


def backup_dir(dir: PathLike):
    dir = Path(dir)
    backup_path = dir.with_name(f"{dir.name}-bak")
    while backup_path.exists():
        backup_path = backup_path.with_name(f"{backup_path.name}-bak")
    os.rename(dir, backup_path)
