from abc import ABC, abstractmethod
from pathlib import Path


class Dependency(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def __eq__(self, value: object) -> bool:
        ...

    @abstractmethod
    def __hash__(self):
        ...


class BuildFile(ABC):
    """
    Abstract class for Build system
    """

    def __init__(self, root: Path, build_files: str):
        self.root = root
        self.build_files = build_files

    @abstractmethod
    def parse_dependencies(self) -> dict[str, list]:
        """
        Sometimes the build_file needs other files inside the project.
        Please make sure the build_file is inside the project.
        """
        ...

    @abstractmethod
    def dumps_dependencies(self, dependencies: dict[str, list]) -> dict[str, str]:
        ...

    @property
    @abstractmethod
    def language(self) -> str:
        ...

    @classmethod
    @abstractmethod
    def is_fake_lib(
        cls,
        dependency: Dependency,
        **kwargs,
    ) -> bool:
        ...

    @property
    @abstractmethod
    def example(self) -> dict:
        ...
