import json

import requests
import tomlkit

from .base import BuildFile, Dependency


class RustDependency(Dependency, tuple[str, dict]):
    """
    Rust Dependency
    str: name
    dict: metadata
        - version: str
        - features: Optional[list[str]]
        - optional: Optional[bool]
        - others ...
    for __eq__: we only compare the name, version, features and optional
    """

    @property
    def name(self) -> str:
        return self[0]

    def canonicalize_name(self, name: str) -> str:
        return name.lower().replace("-", "_")

    def __eq__(self, value: "RustDependency") -> bool:
        if not self.canonicalize_name(self[0]) == self.canonicalize_name(value[0]):
            return False
        if self[1].get("version", None) != value[1].get("version", None):
            return False
        # one features is None and the other is not
        features = set(self[1].get("features", []))
        value_features = set(value[1].get("features", []))
        if features != value_features:
            return False
        optional = self[1].get("optional", None)
        value_optional = value[1].get("optional", None)
        if optional != value_optional:
            return False
        return True

    def __hash__(self):
        # turn dictionary to hashable
        return hash((self[0], json.dumps(self[1], sort_keys=True)))


class RustBuildFile(BuildFile):
    @classmethod
    def is_fake_lib(cls, dependency: RustDependency, **kwargs) -> bool:
        url = f"https://crates.io/api/v1/crates/{dependency.name}/versions"
        response = requests.get(url)
        return response.status_code != 200

    def parse_dependencies(self) -> dict[str, list[RustDependency]]:
        """
        Sometimes the build_file needs other files inside the project.
        Please make sure the build_file is inside the project.
        """
        dependencies = {}
        for file in self.build_files:
            build_file = self.root / file
            with build_file.open() as f:
                toml = tomlkit.parse(f.read())
                if "dependencies" not in toml:
                    deps = {}
                else:
                    deps = toml.item("dependencies").unwrap()
                dependencies[file] = []
                for name, value in deps.items():
                    if isinstance(value, dict):
                        dependency = RustDependency((name, value))
                    else:
                        value = {"version": value}
                        dependency = RustDependency((name, value))
                    dependencies[file].append(dependency)
        return dependencies

    def dumps_dependencies(
        self, dependencies: dict[str, list[RustDependency]]
    ) -> dict[str, str]:
        ret = {}
        for file, deps in dependencies.items():
            with (self.root / file).open() as f:
                toml = tomlkit.parse(f.read())
                deps_dict = {dep[0]: dep[1] for dep in deps}
                toml.update({"dependencies": deps_dict})
                ret[file] = toml.as_string()
        return ret

    @property
    def language(self) -> str:
        return "toml"

    @property
    def example(self) -> dict:
        return dict(
            file="Cargo.toml",
            content="""\
[package]
name = "rust_example"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
""",
        )
