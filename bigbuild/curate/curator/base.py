import logging
import shutil
import subprocess
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any, Dict, List

from bigbuild import RepoInstance
from bigbuild.utils.llm.provider import AzureOpenaiProvider
from bigbuild.utils.log import close_logger, setup_logger

from .make_prompt import make_prompt
from .prompt import ACT_COMMAND_PROMPT, LOCATE_TEST_CI_PROMPT


class _NotSetType:
    def __repr__(self) -> str:
        return "NotSet"

    @property
    def value(self) -> Any:
        return None

    @staticmethod
    def remove_unset_items(data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: value
            for key, value in data.items()
            if not isinstance(value, _NotSetType)
        }


NotSet = _NotSetType()


class Curator:
    instance: RepoInstance

    # internal properties
    root: Path
    logger: logging.Logger
    client: AzureOpenaiProvider

    def __init__(self, instance_dict: dict, root: Path, run_id: str = None):
        self.client = AzureOpenaiProvider("gpt-4o-20240806")
        self.root = root
        repo_instance_fields = {f.name for f in fields(RepoInstance)}
        filtered_data = {
            key: instance_dict.get(key, NotSet) for key in repo_instance_fields
        }
        self.instance = RepoInstance(**filtered_data)
        log_folder = run_id if run_id else "logs/curate"
        self.logger = setup_logger(
            self.instance.instance_id,
            Path("logs/curate") / log_folder / self.instance.instance_id / "curate.log",
        )

    def __del__(self):
        self.logger.info(f">>> DEL >>> Logger: {self.instance.instance_id}")
        close_logger(self.logger)

    def to_dict(self) -> dict:
        res = {
            **asdict(self.instance),
            "ci_file": self.ci_file,
            "act_command": self.act_command,
        }
        return NotSet.remove_unset_items(res)

    def to_mask(self) -> dict:
        res = {
            **self.to_dict(),
            "build_files": self.build_files,
            "patch": self.patch,
            "env_specs": self.env_specs,
        }
        if res["env_specs"]["SDK"] == "N/A":
            res["env_specs"]["SDK"] = res["language"]
        if res["env_specs"]["OS"] == "ubuntu-latest":
            res["env_specs"]["OS"] = "ubuntu-22.04"
        return NotSet.remove_unset_items(res)

    @property
    def act_command(self) -> str | None:
        if self.instance.act_command is NotSet:
            self.set_act_command()
        return self.instance.act_command

    @property
    def build_files(self) -> List[str] | None:
        if self.instance.build_files is NotSet:
            self.set_build_files()
        return self.instance.build_files

    @property
    def ci_file(self) -> str | None:
        if self.instance.ci_file is NotSet:
            self.set_ci_file()
        return self.instance.ci_file

    @property
    def patch(self) -> str | None:
        if self.instance.patch is NotSet:
            self.set_patch()
        return self.instance.patch

    @property
    def env_specs(self) -> dict | None:
        if self.instance.env_specs is NotSet:
            self.set_env_specs()
        return self.instance.env_specs

    def set_act_command(self) -> None:
        self.logger.info(">>> Trying to get >>> ACT Command")
        ci_file_path = self.root / self.ci_file
        with open(ci_file_path, "r") as f:
            ci_content = f.read()
        user_prompt = f"--- Start of {self.ci_file} ---\n{ci_content}\n--- End of {self.ci_file} ---"
        response = self.client.generate_json(
            message=user_prompt,
            system_msg=ACT_COMMAND_PROMPT,
        )[0]
        self.logger.info(f"{response}")
        if not response["act_command"]:
            self.logger.info("Failed to get ACT Command")
            raise Exception("Failed to get ACT Command")
        self.instance.act_command = response["act_command"] + f" -W '{self.ci_file}'"
        self.logger.info(">>> Got >>> ACT Command")

    def set_build_files(self) -> None:
        raise NotImplementedError

    def set_ci_file(self) -> None:
        self.logger.info(">>> Trying to get >>> CI File")
        workflows_path = self.root / ".github" / "workflows"
        if not workflows_path.exists():
            self.logger.info("No workflows found")
            raise Exception("No workflows found")
        ci_content_dict = {}
        for file in workflows_path.glob("*.yml"):
            self.logger.info(f"Found yml {file.relative_to(self.root)}")
            with open(file, "r") as f:
                ci_content_dict[file.relative_to(self.root)] = f.read()
        user_prompt = ""
        for file, content in ci_content_dict.items():
            user_prompt += (
                f"\n --- Start of {file} --- \n{content}\n --- End of {file} --- \n"
            )
        response = self.client.generate_json(
            message=user_prompt,
            system_msg=LOCATE_TEST_CI_PROMPT,
        )[0]
        if not response["ci_file"]:
            self.logger.info("No Test CI file found")
            raise Exception("No Test CI file found")

        self.instance.ci_file = response["ci_file"]
        self.logger.info(f"{response}")
        self.logger.info(">>> Got >>> CI File")

    def set_patch(self) -> None:
        self.sanitize()
        self.mask()
        output = subprocess.run(
            ["git", "diff", "HEAD", "HEAD~1"],
            cwd=self.root,
            capture_output=True,
            text=True,
        )
        self.logger.info(f"Ground Truth Patch: {output.stdout}")
        self.instance.patch = output.stdout

    def set_env_specs(self) -> None:
        self.logger.info(">>> Set Env Specs >>>")
        with open(self.root / self.ci_file) as f:
            ci_content = f.read()
        user_prompt = f"--- Start of {self.ci_file} ---\n{ci_content}\n--- End of {self.ci_file} ---\n## Act command:\n{self.act_command}"
        response = self.client.generate_json(
            message=user_prompt,
            system_msg=make_prompt(self.instance.language),
        )[0]
        self.logger.info(f"{response}")
        if not response["SDK"] or not response["OS"]:
            self.logger.info(">>> Failed to get env specs")
            raise Exception("Failed to get env specs")
        self.instance.env_specs = response

    def sanitize(self) -> None:
        raise NotImplementedError

    def mask(self) -> None:
        raise NotImplementedError

    def commit(self, message: str, repo: Path = None) -> None:
        if repo is None:
            repo = self.root

        add_output = subprocess.run(
            ["git", "add", "."],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )
        self.logger.info(f"Git add output: {add_output.stdout}\n{add_output.stderr}")

        commit_output = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )
        self.logger.info(
            f"Git commit output: {commit_output.stdout}\n{commit_output.stderr}"
        )

    def export(self) -> None:
        self.logger.info("Exporting instance")
        git_dir = self.root / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir)

        output = subprocess.run(
            ["git", "init"],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )
        self.logger.info(f"Git init output: {output.stdout}\n{output.stderr}")

        # add remote
        output = subprocess.run(
            [
                "git",
                "remote",
                "add",
                "origin",
                f"https://github.com/BigBuildBench/{self.instance.instance_id}.git",
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=True,
        )
        self.logger.info(f"Git remote add output: {output.stdout}\n{output.stderr}")

        self.commit("init instance")
