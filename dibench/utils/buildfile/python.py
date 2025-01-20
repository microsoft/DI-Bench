import ast
import configparser
import re
from pathlib import Path

import packaging
import packaging.requirements
import packaging.specifiers
import packaging.version
import requests
import toml
from poetry.core.constraints.version import parse_constraint
from poetry.core.packages.dependency import Dependency as PoetryDependency
from termcolor import colored
from tree_sitter_languages import get_language, get_parser

from .base import BuildFile, Dependency


class PythonDependency(Dependency, packaging.requirements.Requirement):
    @property
    def name(self) -> str:
        return self.name

    # packaging.requirements.Requirement has __eq__ method
    def __eq__(self, value: "PythonDependency") -> bool:
        self_clone = packaging.requirements.Requirement(self.__str__())
        self_clone.name = self.name.lower().replace("-", "_")
        value_clone = packaging.requirements.Requirement(value.__str__())
        value_clone.name = value.name.lower().replace("-", "_")
        return self_clone == value_clone


class PythonBuildSystem(BuildFile):
    @classmethod
    def is_fake_lib(cls, dependency: PythonDependency) -> bool:
        if dependency.url:
            # check the url exists
            response = requests.get(dependency.url)
            return response.status_code != 200
        # check in pypi
        url = f"https://pypi.org/pypi/{dependency.name}/json"
        response = requests.get(url)
        return response.status_code != 200


class VariableVisitor(ast.NodeVisitor):
    def __init__(self):
        self.variables = {}

    def visit_Assign(self, node):
        for target in node.targets:
            if isinstance(target, ast.Name):
                if isinstance(node.value, ast.Name):
                    self.variables[target.id] = self.variables.get(node.value.id, [])
                elif isinstance(node.value, ast.List):
                    self.variables[target.id] = [
                        el.s for el in node.value.elts if isinstance(el, ast.Constant)
                    ]
        self.generic_visit(node)


class SetupTools(PythonBuildSystem):
    def _parse_from_setup_cfg(
        self,
        file_path: Path,
    ) -> list[PythonDependency]:
        config = configparser.ConfigParser()
        config.read(file_path)
        install_requires_str = config.get("options", "install_requires", fallback="")
        install_requires = list(
            filter(
                lambda x: x, map(lambda x: x.strip(), install_requires_str.splitlines())
            )
        )
        packages = []
        for req in install_requires:
            try:
                package = packaging.requirements.Requirement(req)
                packages.append(package)
            except Exception:
                continue
        return packages

    def _parse_from_setup_py(
        self,
        file_path: Path,
    ) -> list[PythonDependency]:
        """
        In our setting, the requirements is defined as a list of strings
        and will `directly` or `indirectly` be assigned to the `install_requires` argument of the `setup` function
        """
        code = file_path.read_bytes()
        language = get_language("python")
        parser = get_parser("python")
        tree = parser.parse(code)
        kwargs_query = language.query(
            """
    (keyword_argument
        name: (identifier) @key
        value: [
            (identifier)
            (list (string)*)
        ] @value
      (#eq? @key "install_requires")
    )
    """
        )
        matches = kwargs_query.matches(tree.root_node)
        var_to_find = None
        for _, match in matches:
            if not match:
                continue
            value = match["value"]
            if value.type == "list":
                try:
                    return [
                        packaging.requirements.Requirement(req)
                        for req in ast.literal_eval(
                            code[value.start_byte : value.end_byte].decode()
                        )
                    ]
                except Exception:
                    list_code = code[value.start_byte : value.end_byte].decode()
                    string_regex = re.compile(r"['\"](.*?)['\"]")
                    return [
                        packaging.requirements.Requirement(req)
                        for req in string_regex.findall(list_code)
                    ]

            var_to_find = code[value.start_byte : value.end_byte].decode()

        visitor = VariableVisitor()
        visitor.visit(ast.parse(code))
        var2val = visitor.variables
        val = var2val.get(var_to_find, [])
        return [packaging.requirements.Requirement(req) for req in val]

    def _dumps_to_setup_cfg(
        self, requirements: list[PythonDependency], build_file: Path
    ) -> str:
        config = configparser.ConfigParser()
        config.read(build_file)
        config.set(
            "options", "install_requires", "\n".join(str(req) for req in requirements)
        )
        import io

        str_buffer = io.StringIO()
        config.write(str_buffer)
        return str_buffer.getvalue()

    def _dumps_to_setup_py(
        self, requirements: list[PythonDependency], build_file: Path
    ) -> str:
        tree = ast.parse(build_file.read_text())
        # find the `install_requires` argument
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "setup":
                    for keyword in node.keywords:
                        if keyword.arg == "install_requires":
                            # replace the value with the new requirements
                            keyword.value = ast.List(
                                elts=[
                                    ast.Constant(value=str(req)) for req in requirements
                                ]
                            )
        return ast.unparse(tree)

    @property
    def language(self) -> str:
        build_file = self.root / self.build_files[0]
        if ".cfg" in build_file.name:
            return "cfg"
        elif ".py" in build_file.name:
            return "python"
        else:
            raise ValueError(f"Unsupported file: {build_file}")

    def parse_dependencies(self) -> dict[str, list[PythonDependency]]:
        build_file = self.root / self.build_files[0]
        if ".cfg" in build_file.name:
            return {self.build_files[0]: self._parse_from_setup_cfg(build_file)}
        elif ".py" in build_file.name:
            return {self.build_files[0]: self._parse_from_setup_py(build_file)}
        else:
            raise ValueError(f"Unsupported file: {build_file}")

    def dumps_dependencies(
        self, requirements: dict[str, list[PythonDependency]]
    ) -> dict[str, str]:
        requirements = requirements[self.build_files[0]]
        build_file = self.root / self.build_files[0]
        if ".cfg" in build_file.name:
            return {
                self.build_files[0]: self._dumps_to_setup_cfg(requirements, build_file)
            }
        elif ".py" in build_file.name:
            return {
                self.build_files[0]: self._dumps_to_setup_py(requirements, build_file)
            }
        else:
            raise ValueError(f"Unsupported file: {build_file}")

    @property
    def example(self) -> dict:
        build_file = self.root / self.build_files[0]
        if ".cfg" in build_file.name:
            return dict(
                file="setup.cfg",
                content="""\
[metadata]
name = example
version = 0.1.0

[options]
zip_safe = False
packages = find:
python_requires = >=3.9
setup_requires = setuptools_scm
install_requires =
    numpy
    requests
""",
            )
        elif ".py" in build_file.name:
            return dict(
                file="setup.py",
                content="""\
from setuptools import setup, find_packages

setup(
    name="example",
    version="0.1.0",
    install_requires=[
        "numpy",
        "requests",
    ],
    packages=find_packages(),
)
""",
            )
        else:
            raise ValueError(f"Unsupported file: {build_file}")


class Pip(PythonBuildSystem):
    # https://pip.pypa.io/en/stable/reference/requirements-file-format/
    # https://peps.python.org/pep-0508/
    # this should parse all relative simple requirements files
    def parse_dependencies(self) -> dict[str, list[PythonDependency]]:
        try:
            # pip >=20
            from pip._internal.network.session import PipSession  # type: ignore
            from pip._internal.req import parse_requirements  # type: ignore
        except ImportError:
            try:
                # 10.0.0 <= pip <= 19.3.1
                from pip._internal.download import PipSession  # type: ignore
                from pip._internal.req import parse_requirements
            except ImportError:
                # pip <= 9.0.3
                from pip.download import PipSession  # type: ignore
                from pip.req import parse_requirements  # type: ignore
        build_file = self.root / self.build_files[0]
        pip_parsed_requirements = list(
            parse_requirements(str(build_file), session=PipSession())
        )

        ret = []
        for req in pip_parsed_requirements:
            try:
                requirement_str = str(req.requirement)
                requirement = packaging.requirements.Requirement(requirement_str)
                ret.append(requirement)
            except Exception:
                continue
        return {self.build_files[0]: ret}

    def dumps_dependencies(
        self, requirements: dict[str, list[PythonDependency]]
    ) -> dict[str, str]:
        requirements = requirements[self.build_files[0]]
        content = "\n".join(str(req) for req in requirements) + "\n"
        return {self.build_files[0]: content}

    @property
    def language(self) -> str:
        return "txt"

    @property
    def example(self) -> dict:
        return dict(
            file="requirements/base.txt",
            content="""\
requests
numpy
""",
        )


class Poetry(PythonBuildSystem):
    def parse_dependencies(self) -> list[PythonDependency]:
        build_file = self.root / self.build_files[0]
        config = toml.load(build_file)
        poetry_dependencies = (
            config.get("tool", {}).get("poetry", {}).get("dependencies", {})
        )
        requirements = set()
        for name, constraint in poetry_dependencies.items():
            if name.lower() == "python":
                continue
            if isinstance(constraint, str):
                constraint = parse_constraint(constraint)
            elif isinstance(constraint, list):
                constraint = parse_constraint(constraint[0].get("version", "*"))
            elif isinstance(constraint, dict):
                constraint = parse_constraint(constraint.get("version", "*"))
            else:
                raise ValueError(f"Unsupported constraint: {constraint}")
            dependency = PoetryDependency(name, constraint=constraint)
            requirements.add(dependency.to_pep_508())
        packages = [packaging.requirements.Requirement(req) for req in requirements]
        return {self.build_files[0]: packages}

    def dumps_dependencies(
        self, requirements: dict[str, list[PythonDependency]]
    ) -> str:
        requirements = requirements[self.build_files[0]]
        build_file = self.root / self.build_files[0]
        config = toml.load(build_file)
        poetry_dependencies = (
            config.get("tool", {}).get("poetry", {}).get("dependencies", {})
        )
        for req in requirements:
            poetry_dependencies[req.name] = str(req.specifier)
        config["tool"]["poetry"]["dependencies"] = poetry_dependencies
        content = toml.dumps(config)
        return {self.build_files[0]: content}

    @property
    def language(self) -> str:
        return "toml"

    @property
    def example(self) -> str:
        return dict(
            file="pyproject.toml",
            content="""\
[project]
name = "example"
version = "0.1.0"

[tool.poetry.dependencies]
requests = "*"
numpy = "*"
""",
        )


class PEP621Compliant(PythonBuildSystem):
    def parse_dependencies(self) -> dict[str, list[PythonDependency]]:
        build_file = self.root / self.build_files[0]
        config = toml.load(build_file)
        requirements = config.get("project", {}).get("dependencies", [])
        packages = [packaging.requirements.Requirement(req) for req in requirements]
        return {self.build_files[0]: packages}

    def dumps_dependencies(
        self,
        requirements: dict[str, list[PythonDependency]],
    ) -> dict[str, str]:
        try:
            requirements = requirements[self.build_files[0]]
            build_file = self.root / self.build_files[0]
            config = toml.load(build_file)
            dump_requirements = config.get("project", {}).get("dependencies", {})
            for req in requirements:
                dump_requirements.append(str(req))
            config["project"]["dependencies"] = dump_requirements
            content = toml.dumps(config)
            return {self.build_files[0]: content}
        except Exception as e:
            print(colored("Failed to dump dependencies", "red"))
            print(e)
            return {self.build_files[0]: ""}

    @property
    def language(self) -> str:
        return "toml"

    @property
    def example(self) -> str:
        return dict(
            file="pyproject.toml",
            content="""\
[project]
name = "example"
version = "0.1.0"
description = "example project"
dependencies = [
    "requests",
    "numpy",
]
""",
        )
