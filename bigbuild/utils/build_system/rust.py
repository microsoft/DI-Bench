from pathlib import Path

import requests
import tomlkit

from .base import BuildSystem, Dependency


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

    def __eq__(self, value: "RustDependency") -> bool:
        if not self[0] == value[0]:
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


class RustBuildSystem(BuildSystem):
    @classmethod
    def is_fake_lib(cls, dependency: RustDependency) -> bool:
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
                deps_dict = {dep.name: dep.raw for dep in deps}
                toml.update({"dependencies": deps_dict})
                ret[file] = toml.as_string()
        return ret

    @property
    def language(self) -> str:
        return "toml"

    @property
    def example(self) -> str:
        return """\
file: Cargo.toml
```toml
[package]
name = "rust_example"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```"""


if __name__ == "__main__":
    from bigbuild.utils import load_bigbuild_dataset
    from bigbuild.utils.repo import get_repo

    dataset = load_bigbuild_dataset("BigBuildBench/BigBuildBench")

    data = None
    for d in dataset:
        if d.language == "rust" and d.instance_id == "jonhoo_faktory-rs":
            data = d
            break

    # get_repo(data, dst=Path(".cache/repo") / data.instance_id)
    build_system = RustBuildSystem(
        root=Path("/home/v-junhaowang/jonhoo_faktory-rs"), build_files=data.build_files
    )

    dependencies = build_system.parse_dependencies()
    print(dependencies)

    get_repo(data, dst=Path(".cache/repo/rust/jonhoo_faktory-rs"))
    build_system = RustBuildSystem(
        root=Path(".cache/repo/rust/jonhoo_faktory-rs"), build_files=data.build_files
    )
    print(build_system.dumps_dependencies(dependencies)["Cargo.toml"])
    print(dependencies["Cargo.toml"])
