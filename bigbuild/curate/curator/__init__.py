from pathlib import Path

from .base import Curator
from .csharp import CsharpCurator
from .java import JavaCurator
from .python import PythonCurator
from .rust import RustCurator
from .typescript import TSCurator

__all__ = ["make_curator"]


def make_curator(instance_dict: dict, root: Path, run_id: Path = None) -> Curator:
    language = instance_dict["language"]
    if language.lower() == "python":
        return PythonCurator(instance_dict, root, run_id)
    elif language.lower() == "csharp":
        return CsharpCurator(instance_dict, root, run_id)
    elif language.lower() == "rust":
        return RustCurator(instance_dict, root, run_id)
    elif language.lower() == "java":
        return JavaCurator(instance_dict, root, run_id)
    elif language.lower() == "typescript" or language.lower() == "javascript":
        return TSCurator(instance_dict, root, run_id)
    raise ValueError(f"Unsupported language: {language}")
