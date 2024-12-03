import shlex
import subprocess
import uuid

from bigbuild.utils.build_system import make_build_system
from bigbuild.utils.build_system.python import Pip
from bigbuild.utils.repo import fake_git_diff

from .base import Builder, Repo

PIGAR_UNKOWN_ERROR = "unknown"
PIGAR_UNCERTAIN_ERROR = "uncertain"

PIGAR_COMPARISON_SPECIFIER = "=="

PIGAR_COMMAND = (
    "pigar generate --auto-select --question-answer yes --include-prereleases"
    " --visit-doc-string --requirement-file {requirements_file}"
    " --exclude-glob **/tests/**"
    " --exclude-glob **/*examples*/**"
    " --exclude-glob **/docs/**"
)


class PigarBuilder(Builder):
    def __init__(self, repo: Repo, with_version: bool):
        self.repo = repo
        self.with_version = with_version

    def patchgen(self) -> str | None:
        requirements_file = f"requirements-{str(uuid.uuid4())[:4]}.txt"
        subprocess.run(
            shlex.split(PIGAR_COMMAND.format(requirements_file=requirements_file)),
            cwd=self.repo.root,
            capture_output=True,
        )
        # remove file content after line "WARNING(pigar): some manual fixes are required"
        # remove line starting with "-e"
        requirements_file = self.repo.root / requirements_file
        lines = requirements_file.read_text().splitlines()
        for i, line in enumerate(lines):
            if "WARNING(pigar): some manual fixes are required" in line:
                lines = lines[:i]
                break
        lines = [line for line in lines if not line.startswith("-e")]
        if not self.with_version:
            lines = [line.split(PIGAR_COMPARISON_SPECIFIER)[0] for line in lines]
        requirements_file.write_text("\n".join(lines))
        pip_system = Pip(
            self.repo.root, [str(requirements_file.relative_to(self.repo.root))]
        )
        requirements = pip_system.parse_dependencies()
        requirements = {
            self.repo.build_files[0]: requirements[
                str(requirements_file.relative_to(self.repo.root))
            ]
        }
        build_system = make_build_system(
            self.repo.language.lower(),
            self.repo.root,
            self.repo.build_files,
        )
        old_content = (self.repo.root / self.repo.build_files[0]).read_text()
        new_content = build_system.dumps_dependencies(requirements)[
            self.repo.build_files[0]
        ]
        # remove the temporary requirements file
        requirements_file.unlink()
        return fake_git_diff(
            "playground",
            {self.repo.build_files[0]: (old_content, new_content)},
        )
