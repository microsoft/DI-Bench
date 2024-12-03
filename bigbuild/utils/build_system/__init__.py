from pathlib import Path

import toml

from .base import BuildSystem, Dependency
from .csharp import CSharpBuildSystem
from .python import PEP621Compliant, Pip, Poetry, SetupTools
from .rust import RustBuildSystem
from .typescript import TypeScriptBuildSystem

__all__ = [
    "make_build_system",
    "BuildSystem",
    "Dependency",
    "PEP621Compliant",
    "Pip",
    "Poetry",
    "SetupTools",
    "RustBuildSystem",
    "CSharpBuildSystem",
    "TypeScriptBuildSystem",
]


def make_build_system(language: str, root: Path, build_files: list[str]) -> BuildSystem:
    if language == "python":
        build_file = root / build_files[0]
        if ".txt" in build_file.name or ".pip" in build_file.name:
            return Pip(root, build_files)
        elif build_file.name == "setup.cfg" or ".py" in build_file.name:
            return SetupTools(root, build_files)
        elif build_file.name == "pyproject.toml":
            data = toml.load(build_file)
            if "tool" in data and "poetry" in data["tool"]:
                return Poetry(root, build_files)
            elif "project" in data:
                return PEP621Compliant(root, build_files)
            else:
                raise ValueError(f"Unsupported file: {build_file}")
        else:
            raise ValueError(f"Unsupported file: {build_file}")
    elif language == "csharp":
        return CSharpBuildSystem(root, build_files)
    elif language == "rust":
        return RustBuildSystem(root, build_files)
    elif language == "typescript" or language == "javascript":
        return TypeScriptBuildSystem(root, build_files)
