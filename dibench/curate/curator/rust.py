from tomlkit import dumps, parse

from .base import Curator


class RustCurator(Curator):
    def set_build_files(self) -> None:
        import glob
        import os

        # recursively search for Cargo.toml files
        res = glob.glob(os.path.join(self.root, "**", "Cargo.toml"), recursive=True)
        res = [os.path.relpath(p, self.root) for p in res]
        self.instance.build_files = res

    def mask(self) -> None:
        for build_file in self.build_files:
            with open(self.root / build_file, "r") as f:
                content = f.read()

            toml = parse(content)
            if "dependencies" in toml:
                self.logger.info(f"Dependencies: {toml['dependencies']}")
                toml["dependencies"] = {}
            else:
                continue
            with open(self.root / build_file, "w") as f:
                f.write(dumps(toml))

        self.commit("MASK")

    def sanitize(self) -> None:
        lock_files = list(self.root.rglob("Cargo.lock"))
        for lock_file in lock_files:
            self.logger.info(f"Deleting {lock_file}")
            lock_file.unlink()
        if lock_files == []:
            self.logger.info("GOOD: No lock files found")
            return
        self.commit("SANITIZE")
