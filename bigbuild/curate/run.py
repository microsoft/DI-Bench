import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from fire import Fire

from bigbuild.utils.ci import run_test_ci
from bigbuild.utils.log import close_logger, setup_logger

RUN_VERIFY_LOG_DIR = Path("logs/verify")


def run_instance(
    instance: dict,
    project_path: Path,
    run_id: str,
    output_jsonl: str,
) -> bool:
    instance_id = instance["instance_id"]
    log_dir = RUN_VERIFY_LOG_DIR / run_id / instance_id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "verify.log"
    logger = setup_logger(instance_id=str(instance_id), log_file=log_file)

    if not project_path.exists():
        raise FileNotFoundError(f"Project path {project_path} does not exist")

    res, _, _ = run_test_ci(
        run_name=instance["instance_id"],
        project_root=project_path,
        command=instance["act_command"],
        logger=logger,
        test_output_file=log_dir / "act_output.log",
    )

    close_logger(logger)

    if res:
        with open(output_jsonl, "a") as f:
            f.write(json.dumps(instance) + "\n")

    return res


def main(
    input_jsonl: str,
    output_jsonl: str,
    cache_dir: str,
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
                    Path(cache_dir) / instance["instance_id"],
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
