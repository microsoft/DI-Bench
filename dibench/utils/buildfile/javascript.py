import json

import requests

from .base import BuildFile, Dependency


class JavaScriptDependency(Dependency, tuple[str, str]):
    """
    JavaScript Dependency
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

    def canonicalize_name(self, name: str) -> str:
        return name.lower().replace("-", "_")

    def __eq__(self, value: "JavaScriptDependency") -> bool:
        return (
            self.canonicalize_name(self[0]) == self.canonicalize_name(value[0])
            and self[1] == value[1]
        )

    def __hash__(self):
        return hash((self.name, self.specifier))


class JavaScriptBuildFile(BuildFile):
    @classmethod
    def is_fake_lib(cls, dependency: Dependency, **kwargs) -> bool:
        result = requests.get(f"https://registry.npmjs.org/{dependency.name}")
        return result.status_code != 200

    def parse_dependencies(self) -> dict[str, list[JavaScriptDependency]]:
        dependencies = {}
        for file in self.build_files:
            build_file = self.root / file
            with build_file.open() as f:
                json_obj = json.load(f)
                deps = json_obj.get("dependencies", {})
                dependencies[file] = []
                for dep, specifier in deps.items():
                    dependency = JavaScriptDependency((dep, specifier))
                    dependencies[file].append(dependency)
        return dependencies

    def dumps_dependencies(
        self, dependencies: dict[str, list[JavaScriptDependency]]
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
    def example(self) -> dict:
        return dict(
            file="package.json",
            content="""\
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
""",
        )
