from pathlib import Path

from .base import Curator, NotSet
from .prompt import ACT_COMMAND_PROMPT_JAVA, LOCATE_TEST_CI_PROMPT_JAVA


class JavaCurator(Curator):
    _entrypoint_path: str
    _build_system: str

    def __init__(self, instance_dict: dict, root: Path):
        super().__init__(instance_dict, root)
        self._entrypoint_path = instance_dict.get("entrypoint_path", NotSet)
        self._build_system = instance_dict.get("build_system", NotSet)

    def to_dict(self) -> dict:
        res = (
            super().to_dict()
            | {"entrypoint_path": self.entrypoint_path}
            | {"build_system": self.build_system}
        )
        return NotSet.remove_unset_items(res)

    def set_ci_file(self) -> None:
        self.logger.info(">>> Trying to get >>> CI File")
        workflows_path = self.root / ".github" / "workflows"
        if not workflows_path.exists():
            self.logger.info("No workflows found")
            raise Exception("No workflows found")

        ci_content_dict = {}
        for file in workflows_path.glob("*.yml"):
            self.logger.info(f"Found yml file {file.relative_to(self.root)}")
            with open(file, "r", encoding="utf-8") as f:
                ci_content_dict[file.relative_to(self.root)] = f.read()

        user_prompt = ""
        for file, content in ci_content_dict.items():
            user_prompt += f"\n --- Start of {file} content --- \n{content}\n --- End of {file} content --- \n"

        response = self.client.generate_json(
            message=user_prompt,
            system_msg=LOCATE_TEST_CI_PROMPT_JAVA,  # Use the Java-specific prompt
        )[0]

        if not response.get("ci_file"):
            self.logger.info("No Test CI file found")
            raise Exception("No Test CI file found")

        self.instance.ci_file = response["ci_file"]
        self.logger.info(f"Response content: {response}")
        self.logger.info(">>> Got >>> CI File")

    def set_act_command(self) -> None:
        self.logger.info(">>> Trying to get >>> Act Command")

        # Ensure that ci_file has been set
        ci_file = self.instance.ci_file
        if not ci_file:
            self.logger.info("CI file not set")
            raise Exception("CI file not set")

        ci_path = self.root / ci_file
        if not ci_path.exists():
            self.logger.info(f"CI file {ci_file} does not exist")
            raise Exception(f"CI file {ci_file} does not exist")

        self.logger.info(f"Reading CI file: {ci_file}")
        with open(ci_path, "r", encoding="utf-8") as f:
            ci_content = f.read()

        self.logger.info("Generating Act Command using AI")
        response = self.client.generate_json(
            message=ci_content,
            system_msg=ACT_COMMAND_PROMPT_JAVA,  # Use the Java-specific ACT command prompt
        )[0]

        act_command = response.get("act_command")
        if not act_command:
            self.logger.info("No Act Command found")
            raise Exception("No Act Command found")

        self.instance.act_command = act_command
        self.logger.info(f"Response content: {response}")
        self.logger.info(">>> Got >>> Act Command")

    def set_build_files(self) -> None:
        pass

    def set_patch(self) -> None:
        pass

    @property
    def entrypoint_path(self) -> str:
        if self._entrypoint_path is NotSet:
            self.set_entrypoint_path()
        return self._entrypoint_path

    @property
    def build_system(self) -> str:
        if self._build_system is NotSet:
            self.set_build_system()
        return self._build_system

    def set_entrypoint_path(self) -> None:
        # Implement logic to set the entry point path for Java projects, such as src/main/java
        java_src = self.root / "src" / "main" / "java"
        if java_src.exists():
            self._entrypoint_path = str(java_src.relative_to(self.root))
            self.logger.info(f"Entrypoint path set to: {self._entrypoint_path}")
        else:
            self.logger.warning("Default Java source entry path not found")
            self._entrypoint_path = ""

    def set_build_system(self) -> None:
        # Detect if the project is using Maven or Gradle
        if (self.root / "pom.xml").exists():
            self._build_system = "Maven"
            self.logger.info("Build system detected: Maven")
        elif (self.root / "build.gradle").exists() or (
            self.root / "build.gradle.kts"
        ).exists():
            self._build_system = "Gradle"
            self.logger.info("Build system detected: Gradle")
        else:
            self.logger.warning("No known build system detected")
            self._build_system = "Unknown"
