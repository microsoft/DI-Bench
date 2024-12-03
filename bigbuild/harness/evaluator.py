import json
import shlex
import shutil
import subprocess
import traceback
import uuid
from pathlib import Path

from bigbuild.harness.constants import (
    APPLY_PATCH_FAIL,
    APPLY_PATCH_PASS,
    CI_TEST_FAIL,
    CI_TEST_PASS,
    EVAL_LOG,
    EVAL_RESULT,
    EXEC_OUTPUT_LOG,
    EXEC_TESTBED,
    GIT_COMMIT_FAIL,
    GIT_COMMIT_PASS,
)
from bigbuild.harness.utils import EvalArgs, EvaluationError
from bigbuild.utils.build_system import Dependency, make_build_system
from bigbuild.utils.ci import run_test_ci
from bigbuild.utils.log import close_logger, setup_logger


class BuildEvaluator:
    def __init__(
        self,
        args: EvalArgs,
    ):
        self.instance_id = args.instance.instance_id
        self.instance = args.instance
        self.project_root = Path(args.project_root).absolute()
        self.prediction = args.prediction
        self.workspace = Path(args.workspace)
        self.log_file = self.workspace / EVAL_LOG
        self.result_file = self.workspace / EVAL_RESULT
        self.logger = setup_logger(
            args.instance.instance_id,
            self.log_file,
        )
        self.exec_eval = args.exec_eval
        self.text_eval = args.text_eval
        self.cache_level = args.cache_level
        self.timeout = args.timeout
        self.resume = args.resume
        self.forest = args.forest
        self.text_result = None
        self.exec_result = None
        self.detail = None

    def _apply_patch(self, testbed: Path, patch_file: Path):
        result = subprocess.run(
            shlex.split(
                f"git apply --allow-empty -v {str(patch_file.relative_to(testbed))}"
            ),
            cwd=testbed,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.logger.info("Failed to apply patch, trying again using unix patch")
            self.logger.info(f"Patch file:\n```diff\n{patch_file.read_text()}")
            self.logger.info(f"git apply error: {result.stderr}")
            result = subprocess.run(
                shlex.split(
                    f"patch --batch --fuzz=5 -p1 -i {str(patch_file.relative_to(testbed))}"
                ),
                cwd=testbed,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.logger.info(f"{APPLY_PATCH_FAIL}:\n{result.stderr}")
                raise EvaluationError(
                    self.instance_id,
                    f"{APPLY_PATCH_FAIL}:\n{result.stderr}",
                    self.logger,
                )
            else:
                self.logger.info(f"{APPLY_PATCH_PASS}\n{result.stdout}")
        else:
            self.logger.info(f"{APPLY_PATCH_PASS}\n{result.stdout}")

    def _git_commit(self, testbed: Path):
        result = subprocess.run(
            ["git", "commit", "-am", "fix build"],
            cwd=testbed,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.logger.info(f"{GIT_COMMIT_FAIL}:\n{result.stdout}")
            raise EvaluationError(
                self.instance_id, f"{GIT_COMMIT_FAIL}:\n{result.stdout}", self.logger
            )
        else:
            self.logger.info(f"{GIT_COMMIT_PASS}:\n{result.stdout}")

    def _ci_test(self, testbed: Path):
        result, _, _ = run_test_ci(
            # self.instance,
            run_name=self.instance_id,
            project_root=testbed,
            command=self.instance.act_command,
            logger=self.logger,
            test_output_file=self.workspace / EXEC_OUTPUT_LOG,
            timeout=self.timeout,
        )
        if not result:
            self.logger.info(CI_TEST_FAIL)
            raise EvaluationError(self.instance_id, CI_TEST_FAIL, self.logger)
        else:
            self.logger.info(CI_TEST_PASS)

    def _clean_workspace(self):
        if self.cache_level == "all":
            # keep all files
            return
        elif self.cache_level == "log":
            # clean all directories
            for item in self.workspace.iterdir():
                if item.is_dir():
                    shutil.rmtree(item)
        elif self.cache_level == "none":
            # remove everything
            shutil.rmtree(self.workspace)

    # ci based execution evaluation
    def _exec_eval(self):
        try:
            if (
                not self.prediction["model_patch"]
                or self.prediction["model_patch"].strip() == ""
            ):
                return "failed to generate"
            testbed = self.workspace / EXEC_TESTBED
            shutil.copytree(self.project_root, testbed)
            # use uuid to avoid filename collision
            patch_file = testbed / f"patch-{uuid.uuid4()}.diff"
            patch_file.write_text(self.prediction["model_patch"])
            self._apply_patch(testbed, patch_file)
            self._git_commit(testbed)
            self._ci_test(testbed)
            return "pass"
        except Exception as e:
            self.logger.error(e)
            self.logger.error(traceback.format_exc())
            return "failed for test"

    def __parse_dependencies_from_patch(self, testbed: Path, patch: str) -> dict:
        if patch is None or len(patch.strip()) == 0:
            return {file: [] for file in self.instance.build_files}
        build_system = make_build_system(
            self.instance.language.lower(), testbed, self.instance.build_files
        )
        patch_file = testbed / f"patch-{uuid.uuid4()}.diff"
        patch_file.write_text(patch)
        self._apply_patch(testbed, patch_file)
        return build_system.parse_dependencies()

    def __compute_textual_metric(
        self,
        model_deps: list[Dependency],
        oracle_deps: list[Dependency],
    ) -> dict:
        true_positives = len([dep for dep in model_deps if dep in oracle_deps])
        false_positives = len([dep for dep in model_deps if dep not in oracle_deps])
        false_negatives = len([dep for dep in oracle_deps if dep not in model_deps])
        exact = dict(
            TP=true_positives,
            FP=false_positives,
            FN=false_negatives,
        )

        model_dep_names: set[str] = set([dep.name for dep in model_deps])
        oracle_dep_names: set[str] = set([dep.name for dep in oracle_deps])
        true_positives = len(model_dep_names & oracle_dep_names)
        false_positives = len(model_dep_names - oracle_dep_names)
        false_negatives = len(oracle_dep_names - model_dep_names)
        name_only = dict(
            TP=true_positives,
            FP=false_positives,
            FN=false_negatives,
        )
        return dict(exact=exact, name_only=name_only)

    def _text_eval(self) -> dict:
        exact_result = dict(
            TP=0,
            FP=0,
            FN=0,
        )
        name_only_result = dict(
            TP=0,
            FP=0,
            FN=0,
        )
        fake_libs = 0
        self.detail = dict(predicted=dict(), oracle=dict())
        try:
            oracle_testbed = self.workspace / "oracle_text_testbed"
            shutil.copytree(self.project_root, oracle_testbed)
            oracle_dependencies = self.__parse_dependencies_from_patch(
                oracle_testbed, self.instance.patch
            )
            self.detail["oracle"] = {
                file: [dep.name for dep in deps]
                for file, deps in oracle_dependencies.items()
            }
            model_testbed = self.workspace / "model_text_testbed"
            shutil.copytree(self.project_root, model_testbed)
            model_dependencies = self.__parse_dependencies_from_patch(
                model_testbed, self.prediction["model_patch"]
            )
            self.detail["predicted"] = {
                file: [dep.name for dep in deps]
                for file, deps in model_dependencies.items()
            }
            build_system = make_build_system(
                self.instance.language.lower(), model_testbed, self.instance.build_files
            )
            assert oracle_dependencies.keys() == model_dependencies.keys()
            for file in oracle_dependencies.keys():
                result = self.__compute_textual_metric(
                    model_dependencies[file], oracle_dependencies[file]
                )
                fake_libs += sum(
                    build_system.is_fake_lib(dep) for dep in model_dependencies[file]
                )
                exact_result["TP"] += result["exact"]["TP"]
                exact_result["FP"] += result["exact"]["FP"]
                exact_result["FN"] += result["exact"]["FN"]
                name_only_result["TP"] += result["name_only"]["TP"]
                name_only_result["FP"] += result["name_only"]["FP"]
                name_only_result["FN"] += result["name_only"]["FN"]
            return dict(
                exact=exact_result, name_only=name_only_result, fake_libs=fake_libs
            )
        except Exception as e:
            self.logger.error(e)
            self.logger.error(traceback.format_exc())
            return dict(exact=exact_result, name_only=name_only_result)

    def run(self) -> dict:
        if self.result_file.exists() and self.resume:
            with open(self.workspace / "result.json", "r") as f:
                result = json.load(f)
                assert self.instance_id == result.get("instance_id", None)
                self.text_result = result["text"]
                self.exec_result = result["exec"]
                self.detail = result["detail"]
                return
        if self.text_eval:
            self.text_result = self._text_eval()
        if self.exec_eval:
            self.exec_result = self._exec_eval()
        with open(self.result_file, "w") as f:
            f.write(json.dumps(self.result, indent=2))
        self._clean_workspace()

    @property
    def result(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "text": self.text_result,
            "exec": self.exec_result,
            "detail": self.detail,
        }

    def __del__(self):
        close_logger(self.logger)
