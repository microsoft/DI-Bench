import json
from pathlib import Path

import requests

from .base import BuildSystem, Dependency


class TypeScriptDependency(Dependency, tuple[str, str]):
    """
    TypeScript Dependency
    str: name
    str: specifier

    "foo": "1.0.0 - 2.9999.9999",
    "bar": ">=1.0.2 <2.1.2",
    "baz": ">1.0.2 <=2.3.4",
    "boo": "2.0.1",
    "qux": "<1.0.0 || >=2.3.1 <2.4.5 || >=2.5.2 <3.0.0",
    "asd": "http://asdf.com/asdf.tar.gz",
    "til": "~1.2",
    "elf": "~1.2.3",
    "two": "2.x",
    "thr": "3.3.x",
    "lat": "latest",
    "dyl": "file:../dyl",
    "kpg": "npm:pkg@1.0.0"

    for __eq__: we compare the name, specifier
    """

    @property
    def name(self) -> str:
        return self[0]

    @property
    def specifier(self) -> str:
        return self[1]

    def __eq__(self, value: "TypeScriptDependency") -> bool:
        return self[0] == value[0] and self[1] == value[1]


class TypeScriptBuildSystem(BuildSystem):
    @classmethod
    def is_fake_lib(cls, dependency: Dependency) -> bool:
        result = requests.get(f"https://registry.npmjs.org/{dependency.name}")
        return result.status_code != 200

    def parse_dependencies(self) -> dict[str, list[TypeScriptDependency]]:
        dependencies = {}
        for file in self.build_files:
            build_file = self.root / file
            with build_file.open() as f:
                json_obj = json.load(f)
                deps = json_obj.get("dependencies", {})
                dependencies[file] = []
                for dep, specifier in deps.items():
                    dependency = TypeScriptDependency((dep, specifier))
                    dependencies[file].append(dependency)
        return dependencies

    def dumps_dependencies(
        self, dependencies: dict[str, list[TypeScriptDependency]]
    ) -> dict[str, str]:
        ret = {}
        for file, deps in dependencies.items():
            with (self.root / file).open() as f:
                json_obj = json.load(f)
                deps_dict = {dep.name: dep.specifier for dep in deps}
                json_obj["dependencies"] = deps_dict
                ret[file] = json.dumps(json_obj, indent=2)
        return ret

    @property
    def language(self) -> str:
        return "json"

    @property
    def example(self) -> str:
        return """\
file: package.json
```json
{
  "name": "typescript-example",
  "version": "0.0.1",
  "type": "module",
  "scripts": {
    "build": "tsc && vite build",
    "dev": "vite",
    "prepare": "husky",
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "zustand": "^4.5.2"
  },
  "devDependencies": {
    "husky": "^9.0.11",
    "typescript": "^5.3.2",
    "vite": "^4.4.5"
  }
}
```"""


if __name__ == "__main__":
    from bigbuild.utils import load_bigbuild_dataset

    dataset = load_bigbuild_dataset("BigBuildBench/BigBuildBench-Mini")

    data = None
    for d in dataset:
        if d.language == "typescript":
            data = d
            break

    build_system = TypeScriptBuildSystem(
        root=Path("/data2/linghao/raw_ts") / data.instance_id,
        build_files=data.build_files,
    )
    dependencies = build_system.parse_dependencies()
    print(dependencies)
    filtered = TypeScriptBuildSystem.filter_invalid_dependencies(dependencies)
    print(filtered)
    dumped = build_system.dumps_dependencies(filtered)
    print(dumped)
