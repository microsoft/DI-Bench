import logging
import time
import uuid
from pathlib import Path

import docker
from docker.models.containers import Container

from bigbuild.utils.docker import container_context


def wait_for_docker_daemon(
    container: Container, logger: logging.Logger, timeout: int = 60
):
    start_time = time.time()
    while True:
        exit_code, _ = container.exec_run("docker ps")
        if exit_code == 0:
            logger.info("Docker daemon started.")
            break
        elif time.time() - start_time > timeout:
            raise TimeoutError("Waited too long for Docker daemon to start.")
        else:
            logger.info("Waiting for Docker daemon to start...")
            time.sleep(2)


def run_test_ci(
    run_name: str,
    project_root: Path,
    command: str,
    logger: logging.Logger,
    test_output_file: Path,
    timeout: int = 1200,
) -> tuple[bool, str, str]:
    container_name = f"bigbuild-{run_name}-{str(uuid.uuid4())[:6]}"
    client = docker.from_env(timeout=200)
    with container_context(
        client=client,
        logger=logger,
        project_path=project_root,
        name=container_name,
    ) as container:
        wait_for_docker_daemon(container, logger)
        exit_code, output = container.exec_run("ls")
        logger.info(f"ls /project: {output.decode()}")
        logger.info(f"Running ACT command: {command}")
        exit_code, (stdout, stderr) = container.exec_run(
            cmd=f"timeout {timeout}s {command}", demux=True
        )
        stdout = stdout.decode()
        stderr = stderr.decode()
        test_output_file.write_text(
            f"===== stdout =====\n{stdout}\n===== stderr =====\n{stderr}"
        )

    # a hack to get the result of whether CI passed or failed
    # a workaround but somewhat reliable
    if "🏁  Job failed" in stdout or int(exit_code) == 124:
        # if command times out, it will return 124 with no Job failed message
        logger.error(f"ACT command failed, exit code: {exit_code}")
        return False, stdout, stderr
    if "🏁  Job succeeded" in stdout:
        logger.info(f"ACT command succeeded, exit code: {exit_code}")
        return True, stdout, stderr
    # in case of skipping unsupported platform
    logger.info(f"ACT command failed, has been skipped, exit code: {exit_code}")
    return False, stdout, stderr
