from dataclasses import dataclass
from typing import List


@dataclass
class RepoInstance:
    instance_id: str
    metadata: dict  # include repo_name, commit_hash, etc. whatever you want :)
    language: str
    act_command: str
    ci_file: str
    patch: str
    build_files: List[str]
    env_specs: dict[str, str]
