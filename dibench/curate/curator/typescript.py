import json
import os

from .base import Curator


class TSCurator(Curator):
    def set_build_files(self) -> None:
        build_files = []

        json_files = list(self.root.rglob("package.json"))
        for json_file in json_files:
            with open(json_file, "r") as f:
                json_data = json.load(f)
            if "dependencies" in json_data:
                build_files.append(os.path.relpath(json_file, self.root))

        if build_files == []:
            raise FileNotFoundError("No package.json files found")

        self.instance.build_files = build_files

    def mask(self) -> None:
        for build_file in self.build_files:
            with open(self.root / build_file, "r") as f:
                json_data = json.load(f)

            if "dependencies" in json_data:
                self.logger.info(f"Dependencies: {json_data['dependencies']}")
                del json_data["dependencies"]
            else:
                raise KeyError("dependencies not found in package.json")

            with open(self.root / build_file, "w") as f:
                f.write(json.dumps(json_data, indent=2) + "\n")

        self.commit("MASK")

    def sanitize(self) -> None:
        lock_files = (
            list(self.root.rglob("yarn.lock"))
            + list(self.root.rglob("package-lock.json"))
            + list(self.root.rglob("pnpm-lock.yaml"))
            + list(self.root.rglob("npm-shrinkwrap.json"))
        )
        for lock_file in lock_files:
            self.logger.info(f"Deleting {lock_file}")
            lock_file.unlink()
        if lock_files == []:
            self.logger.info("GOOD: No lock files found")
            return
        self.commit("SANITIZE")
