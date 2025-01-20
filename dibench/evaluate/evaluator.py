import json
import shlex
import shutil
import subprocess
import traceback
import uuid
from collections import defaultdict
from pathlib import Path

from dibench.evaluate.constants import (
    APPLY_PATCH_FAIL,
    APPLY_PATCH_PASS,
    CI_TEST_FAIL,
    CI_TEST_PASS,
    EVAL_LOG,
    EVAL_RESULT,
    GIT_COMMIT_FAIL,
    GIT_COMMIT_PASS,
)
from dibench.evaluate.utils import EvalArgs, EvaluationError
from dibench.utils.buildfile import Dependency, make_buildfile
from dibench.utils.ci import run_test_ci
from dibench.utils.log import close_logger, setup_logger


class BuildEvaluator:
    def __init__(
        self,
        args: EvalArgs,
    ):
        self.resume = args.resume
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
        self.text_result = None
        self.exec_result = None
        self.patch_exec_result = None
        self.remove_fake_result = None
        self.detail = None
        self.patch_exec_result = None

    def _apply_patch(self, testbed: Path, patch_file: Path):
        result = subprocess.run(
            shlex.split(
                f"git apply --allow-empty -v --ignore-whitespace --ignore-space-change {str(patch_file.relative_to(testbed))}"
            ),
            cwd=testbed,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.logger.info("Failed to apply patch, trying again using unix patch")
            self.logger.info(f"Patch file:\n```diff\n{patch_file.read_text()}```")
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

    def _ci_test(self, testbed: Path, output_file: str):
        result, _, _ = run_test_ci(
            # self.instance,
            run_name=self.instance_id,
            project_root=testbed,
            command=self.instance.act_command,
            logger=self.logger,
            test_output_file=self.workspace / output_file,
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
            self._ci_test(self.model_root, "exec-output.log")
            return "pass"
        except Exception as e:
            self.logger.error(e)
            self.logger.error(traceback.format_exc())
            return "fail"

    def __parse_dependencies(self, testbed: Path) -> dict:
        """
        Parse dependencies from a given patch.

        This method extracts dependencies specified in the patch file for a
        particular testbed. If the patch is empty or None, it returns an empty
        list for each build file associated with the instance. Otherwise, it
        utilizes the build system to parse and return the dependencies.

        :param testbed: The path to the testbed directory.
        :param patch: The patch string containing dependency changes.
        :return: A dictionary where keys are build files and values are lists
                 of dependencies.
        """
        build_system = make_buildfile(
            self.instance.language.lower(), testbed, self.instance.build_files
        )
        return build_system.parse_dependencies()

    def __compute_textual_metric(
        self,
        model_deps: list[Dependency],
        oracle_deps: list[Dependency],
    ) -> dict:
        """
        Compute the textual metrics for the given model and oracle dependencies.

        :param model_deps: Model's dependencies
        :param oracle_deps: Oracle's dependencies
        :return: A dictionary containing the textual metrics:
            - exact: a dictionary with TP, FP, FN for exact matches
            - name_only: a dictionary with TP, FP, FN for name-only matches
        """
        model_deps_set = set(model_deps)
        oracle_deps_set = set(oracle_deps)
        tp = len(model_deps_set.intersection(oracle_deps_set))
        fp = len(model_deps_set.difference(oracle_deps_set))
        fn = len(oracle_deps_set.difference(model_deps_set))
        assert tp + fn == len(oracle_deps_set)
        assert tp + fp == len(model_deps_set)
        exact = dict(
            TP=tp,
            FP=fp,
            FN=fn,
        )

        model_dep_names: set[str] = set(
            [dep.name.lower().replace("-", "_") for dep in model_deps]
        )
        oracle_dep_names: set[str] = set(
            [dep.name.lower().replace("-", "_") for dep in oracle_deps]
        )
        tp = len(model_dep_names.intersection(oracle_dep_names))
        fp = len(model_dep_names.difference(oracle_dep_names))
        fn = len(oracle_dep_names.difference(model_dep_names))
        assert tp + fn == len(oracle_dep_names)
        assert tp + fp == len(model_dep_names)
        name_only = dict(
            TP=tp,
            FP=fp,
            FN=fn,
        )
        return dict(exact=exact, name_only=name_only)

    def _text_eval(self, oracle_dependencies: dict, model_dependencies: dict) -> dict:
        """
        Evaluate the textual metrics by comparing the model's predictions with the oracle's predictions.

        :param oracle_dependencies: The oracle's dependencies for each build file.
        :param model_dependencies: The model's dependencies for each build file.
        :return: A dictionary containing the textual metrics: exact and name_only.
        """
        assert (
            oracle_dependencies.keys() == model_dependencies.keys()
        ), "Build files mismatch"
        build_system = make_buildfile(
            self.instance.language.lower(),
            self.oracle_root,
            self.instance.build_files,
        )
        # Initialize the counters for the textual metrics
        exact_result, name_only_result = defaultdict(int), defaultdict(int)
        fake_libs = 0
        for file in oracle_dependencies.keys():
            # Compute the textual metrics for each build file
            result = self.__compute_textual_metric(
                model_dependencies[file], oracle_dependencies[file]
            )
            # Count the number of fake libraries in the model's predictions
            # for csharp
            if self.instance.language.lower() == "csharp":
                kwargs = dict(
                    project_root=self.model_root,
                    build_file=file,
                )
            else:
                kwargs = dict()
            fake_libs += sum(
                build_system.is_fake_lib(dep, **kwargs)
                for dep in model_dependencies[file]
            )
            # Update the counters for the textual metrics
            exact_result["TP"] += result["exact"]["TP"]
            exact_result["FP"] += result["exact"]["FP"]
            exact_result["FN"] += result["exact"]["FN"]
            name_only_result["TP"] += result["name_only"]["TP"]
            name_only_result["FP"] += result["name_only"]["FP"]
            name_only_result["FN"] += result["name_only"]["FN"]
        # Store the textual metrics in the object
        self.text_result = dict(
            exact=exact_result, name_only=name_only_result, fake_libs=fake_libs
        )

    def run(self) -> dict:
        """
        Executes the evaluation process by setting up the oracle and model workspaces,
        applying patches, performing text and execution evaluations, and saving the results.

        This function performs the following steps:
        1. Creates an oracle workspace by copying the project root and applies the oracle patch.
        2. Creates a model workspace by copying the project root and applies the prediction patch.
        3. Conducts a text evaluation to compare the model's prediction against the oracle.
        4. If enabled, performs an execution evaluation.
        5. If patch evaluation is enabled and the language is Python, performs a patch execution evaluation.
        6. Writes the evaluation results to a result file.
        7. Cleans up the workspace by removing temporary files and directories.

        Returns:
            A dictionary containing the evaluation results.
        """
        self.oracle_root = self.workspace / "oracle"
        if self.oracle_root.exists():
            shutil.rmtree(self.oracle_root)
        shutil.copytree(self.project_root, self.oracle_root, symlinks=True)
        patch_file = self.oracle_root / f"patch-{str(uuid.uuid4())[:4]}.diff"
        patch_file.write_text(self.instance.patch)
        self._apply_patch(self.oracle_root, patch_file)
        self.oracle_dependencies = self.__parse_dependencies(self.oracle_root)
        self.detail = dict()
        self.detail["oracle"] = {
            file: [dep.name for dep in deps]
            for file, deps in self.oracle_dependencies.items()
        }
        assert self.instance.build_files == list(
            self.oracle_dependencies.keys()
        ), "Build files mismatch"

        self.model_root = self.workspace / "model"
        try:
            if self.model_root.exists():
                shutil.rmtree(self.model_root)
            shutil.copytree(self.project_root, self.model_root, symlinks=True)
            patch_file = self.model_root / f"patch-{str(uuid.uuid4())[:4]}.diff"
            patch_file.write_text(self.prediction)
            self._apply_patch(self.model_root, patch_file)
            self.model_dependencies = self.__parse_dependencies(self.model_root)
            for file in self.instance.build_files:
                if file not in self.model_dependencies:
                    self.model_dependencies[file] = []
        except Exception as _:
            self.logger.warning(
                "Failed to parse dependencies for model generated patch"
            )
            self.model_dependencies = {file: [] for file in self.instance.build_files}

        self.detail["predicted"] = {
            file: [dep.name for dep in deps]
            for file, deps in self.model_dependencies.items()
        }
        self._text_eval(
            oracle_dependencies=self.oracle_dependencies,
            model_dependencies=self.model_dependencies,
        )
        results = {}
        if self.result_file.exists():
            results = json.loads(self.result_file.read_text())
            if results.get("exec", None) is not None:
                self.exec_result = results["exec"]
            if results.get("patch-exec", None) is not None:
                self.patch_exec_result = results["patch-exec"]
            if results.get("remove-fake", None) is not None:
                self.remove_fake_result = results["remove-fake"]
        if self.exec_eval:
            if not self.resume or results.get("exec", None) is None:
                self.exec_result = self._exec_eval()
            else:
                exec_output_log = self.workspace / "exec-output.log"
                if exec_output_log.exists():
                    self.exec_result = results["exec"]
                else:
                    print("No exec output log found, re-running")
                    self.exec_result = self._exec_eval()
        if self.patch_eval:
            if not self.resume or results.get("patch-exec", None) is None:
                self.patch_exec_result = self._patch_eval()
            else:
                self.patch_exec_result = results["patch-exec"]
        if self.remove_fake_eval:
            if not self.resume or results.get("remove-fake", None) is None:
                self.remove_fake_result = self._remove_fake_eval()
            else:
                self.remove_fake_result = results["remove-fake"]
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
