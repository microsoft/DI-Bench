import tomlkit

from .base import Curator


class PythonCurator(Curator):
    def sanitize(self) -> None:
        lock_files = list(self.root.rglob("poetry.lock")) + list(
            self.root.rglob("Pipfile.lock")
        )
        for lock_file in lock_files:
            self.logger.info(f"Deleting {lock_file}")
            lock_file.unlink()
        if lock_files == []:
            self.logger.info("GOOD: No lock files found")
            return
        self.commit("SANITIZE")

    def mask(self) -> None:
        self.logger.info(">>> Masking >>>")
        toml_path = self.root / "pyproject.toml"
        if not toml_path.exists():
            raise FileNotFoundError(f"pyproject.toml not found in {self.root}")
        data = tomlkit.loads(toml_path.read_text())
        project_dep = data.get("project", {}).get("dependencies", {})
        poetry_dep = data.get("tool", {}).get("poetry", {}).get("dependencies", {})

        if not project_dep and not poetry_dep:
            self.logger.info(">>> No dependencies found")
            raise Exception("No dependencies found")

        if project_dep and poetry_dep:
            self.logger.info(">>> Both project and poetry dependencies found")
            raise Exception("Both project and poetry dependencies found")

        if project_dep:
            data["project"]["dependencies"] = []
        if poetry_dep:
            poetry_dependencies = data["tool"]["poetry"]["dependencies"]
            new_dependencies = {
                k: v for k, v in poetry_dependencies.items() if k.lower() == "python"
            }
            data["tool"]["poetry"]["dependencies"] = new_dependencies

        with open(toml_path, "w") as f:
            f.write(tomlkit.dumps(data))

        self.commit("MASK")

    def set_build_files(self) -> None:
        self.instance.build_files = ["pyproject.toml"]
