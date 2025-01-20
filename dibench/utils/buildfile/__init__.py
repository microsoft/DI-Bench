from pathlib import Path

import toml

from .base import BuildFile, Dependency
from .csharp import CSharpBuildFile
from .javascript import JavaScriptBuildFile
from .python import PEP621Compliant, Pip, Poetry, SetupTools
from .rust import RustBuildFile

__all__ = [
    "make_buildfile",
    "BuildFile",
    "Dependency",
    "PEP621Compliant",
    "Pip",
    "Poetry",
    "SetupTools",
    "RustBuildFile",
    "CSharpBuildFile",
    "JavaScriptBuildFile",
]


def make_buildfile(language: str, root: Path, build_files: list[str]) -> BuildFile:
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
        return CSharpBuildFile(root, build_files)
    elif language == "rust":
        return RustBuildFile(root, build_files)
    elif language == "typescript" or language == "javascript":
        return JavaScriptBuildFile(root, build_files)
