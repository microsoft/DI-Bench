import json
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from fire import Fire

from bigbuild.utils.ci import run_test_ci
from bigbuild.utils.log import close_logger, setup_logger

RUN_VERIFY_LOG_DIR = Path("logs/verify")


def run_instance(
    instance: dict,
    root: Path,
    run_id: str,
    output_jsonl: str,
) -> bool:
    instance_id = instance["instance_id"]
    log_dir = RUN_VERIFY_LOG_DIR / run_id / instance_id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "verify.log"
    logger = setup_logger(instance_id=str(instance_id), log_file=log_file)

    if not root.exists():
        raise FileNotFoundError(f"Project path {root} does not exist")

    with tempfile.TemporaryDirectory() as playground:
        logger.info(">>> Start to verify patch applied on")
        shutil.copytree(root, Path(playground) / instance_id, symlinks=True)
        patch = instance.get("patch")
        patch_path = Path(playground) / instance_id / "patch.diff"
        patch_path.write_text(patch)

        logger.info("Using git apply")
        output = subprocess.run(
            ["git", "apply", str(patch_path)],
            cwd=str(Path(playground) / instance_id),
            capture_output=True,
            text=True,
        )
        if output.returncode != 0:
            logger.info("Git apply failed")
            output = subprocess.run(
                ["patch", "--batch", "--fuzz=5", "-p1", "-i", str(patch_path)],
                cwd=str(Path(playground) / instance_id),
                capture_output=True,
                text=True,
            )
            if output.returncode != 0:
                logger.info("Patch failed")
                logger.info(">>> Apply failed. Exit.")
                return False

        logger.info(f"Patch applied\n{output.stdout}")

        res, _, _ = run_test_ci(
            run_name=instance["instance_id"],
            project_root=Path(playground) / instance_id,
            command=instance["act_command"],
            logger=logger,
            test_output_file=log_dir / "apply_output.log",
        )

        if not res:
            logger.info(">>> Failed when apply patch. Exit.")
            return False
        logger.info(">>> Success when apply gold patch, good.")

    # need fail
    logger.info(">>> Start to verify deps been masked")
    res, _, _ = run_test_ci(
        run_name=instance["instance_id"],
        project_root=root,
        command=instance["act_command"],
        logger=logger,
        test_output_file=log_dir / "masked_output.log",
    )

    if res:
        logger.info(">>> Success when deps been masked. Exit.")
        close_logger(logger)
        return False

    logger.info(">>> Failed when deps been masked. Instance is valid.")

    with open(output_jsonl, "a") as f:
        f.write(json.dumps(instance) + "\n")

    close_logger(logger)
    return True


def main(
    input_jsonl: str,
    output_jsonl: str,
    instance_dir: str,
    run_id: str,
    concurrency: int = 10,
):
    suc_count = 0
    total_count = 0
    with open(input_jsonl, "r") as f:
        instances = [json.loads(line) for line in f]
    print(f"Total instances: {len(instances)}")

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        from alive_progress import alive_bar

        with alive_bar(len(instances)) as bar:
            futures = [
                executor.submit(
                    run_instance,
                    instance,
                    Path(instance_dir) / instance["instance_id"],
                    run_id,
                    output_jsonl,
                )
                for instance in instances
            ]
            for future in as_completed(futures):
                try:
                    res = future.result()
                    if res:
                        suc_count += 1
                except Exception as e:
                    print(e)
                total_count += 1
                bar.text(f"Success: {suc_count}/{total_count}")
                bar()

    print(f"Success: {suc_count}/{total_count}")


if __name__ == "__main__":
    Fire(main)
