from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Repo",
    "Builder",
]


@dataclass
class Repo:
    """Repo information for building."""

    name: str
    root: Path
    language: str
    build_files: tuple[str]
    env_specs: dict[str, str]


class Builder(ABC):
    def __init__(self, repo: Repo):
        self.repo = repo

    @abstractmethod
    def patchgen(self) -> str | None:
        ...
