"""Utility functions to interact with Docker containers and images."""

import logging
import os
import pathlib
import platform
import re
import tarfile
import tempfile
import threading
import time
import traceback
from contextlib import contextmanager

import docker
import docker.client
import docker.errors
from docker.models.containers import Container

ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

ARCH = platform.machine()

if ARCH == "arm64":
    PLATFORM = "linux/arm64/v8"
elif ARCH == "x86_64":
    PLATFORM = "linux/x86_64"
else:
    raise ValueError(f"Unsupported architecture: {ARCH}")

WORKDIR = pathlib.Path("/testbed/")


def build_container(
    client: docker.DockerClient,
    logger: logging.Logger,
    name: str,
    project_path: pathlib.Path,
    image_name: str = "justachillguy/dibench-runner",
):
    """
    Build a Docker container from an image

    Args:
        client: Docker client
        image_name: Name of the image to build container from

    Returns:
        Docker container
    """
    project_path = project_path.absolute()
    try:
        client.images.get(image_name)
        logger.info(f"Image exists: {image_name}")
    except docker.errors.ImageNotFound:
        logger.info(f"Image not found: {image_name}")
        try:
            client.images.pull(image_name)
            logger.info(f"Pulled image: {image_name}")
        except Exception as e:
            logger.error(f"Failed to pull image: {image_name}, error: {e}")
            raise e
    except Exception as e:
        logger.error(f"Failed to get image: {image_name}, error: {e}")
        raise e

    logger.info(f"Creating container from image: {image_name}")
    try:
        container = client.containers.create(
            image=image_name,
            detach=True,
            name=name,
            tty=True,
            environment={"GITHUB_TOKEN": os.getenv("GITHUB_TOKEN")},
            stdin_open=True,
            runtime="sysbox-runc",
            volumes={
                str(project_path): {
                    "bind": "/project",
                    "mode": "ro",
                }
            },
        )
        logger.info(f"Container created: {container.name}")
    except Exception as e:
        logger.error(f"Failed to create container from image: {image_name}, error: {e}")
        raise e
    return container


@contextmanager
def container_context(
    client: docker.DockerClient,
    logger: logging.Logger,
    name: str,
    project_path: pathlib.Path,
    image_name: str = "justachillguy/dibench-runner",
):
    """
    Context manager to create a container from an image and cleanup after use
    """
    container = None
    try:
        container = build_container(client, logger, name, project_path, image_name)
        logger.info(f"Starting container: {container.name}")
        container.start()
        while True:
            container.reload()
            if container.status == "running":
                logger.info(f"Container {container.name} is running")
                break
            logger.info(f"Waiting for container {container.name} to start...")
            time.sleep(1)
        yield container
    except Exception as e:
        logger.error(f"Error in container context: {e}")
        raise e
    finally:
        if container:
            cleanup_container(container, logger)


def cleanup_container(
    container: Container,
    logger: logging.Logger,
) -> None:
    if not container:
        return

    # Attempt to stop the container
    try:
        if container:
            logger.info(f"Attempting to stop container {container.name}...")
            container.stop()
    except Exception as e:
        logger.error(
            f"Failed to stop container {container.name}: {e}. Trying to forcefully kill..."
        )
        try:
            # Get the PID of the container
            container_info = container.attrs
            pid = container_info["State"].get("Pid", 0)

            # If container PID found, forcefully kill the container
            if pid > 0:
                logger.info(
                    f"Forcefully killing container {container.name} with PID {pid}..."
                )
                container.kill()
            else:
                logger.error(
                    f"PID for container {container.name}: {pid} - not killing."
                )
        except Exception as e2:
            logger.error(
                f"Failed to forcefully kill container {container.name}: {e2}\n"
                f"{traceback.format_exc()}"
            )

    # Attempt to remove the container

    max_retries = 3

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"Attempting to remove container {container.name}... (Attempt {attempt}/{max_retries})"
            )
            container.remove(force=True, v=True)
            logger.info(f"Container {container.name} removed.")
            break
        except Exception as e:
            logger.error(f"Failed to remove container {container.name}: {e}\n")
            if attempt < max_retries:
                logger.info(f"Retrying to remove container {container.name}...")
            else:
                logger.error(
                    f"Failed to remove container {container.name} after {max_retries} attempts."
                )
                print(
                    f"Failed to remove container {container.name}, please pay attention to this."
                )


def copy_to_container(container: Container, src: pathlib.Path, dst: pathlib.Path):
    """
    Copy a file from local to a docker container

    Args:
        container (Container): Docker container to copy to
        src (Path): Source file path
        dst (Path): Destination file path in the container
    """
    # Ensure src is a directory
    if not src.is_dir():
        raise ValueError("Source path must be a directory")

    import io

    # Create a tar archive of the contents of src
    tarstream = io.BytesIO()
    with tarfile.open(fileobj=tarstream, mode="w") as tar:
        for item in src.iterdir():
            tar.add(item, arcname=item.name)
    tarstream.seek(0)

    # Ensure dst is a string
    dst_str = str(dst)

    # Optionally, create the destination directory in the container
    # Run 'mkdir -p dst' in the container to ensure the directory exists
    exit_code, output = container.exec_run(f"mkdir -p {dst_str}")
    if exit_code != 0:
        raise RuntimeError(
            f"Error creating directory {dst_str} in container: {output.decode()}"
        )

    # Now put the archive into the container at dst
    success = container.put_archive(dst_str, tarstream.getvalue())
    if not success:
        raise RuntimeError(f"Failed to copy archive to container at {dst_str}")


def copy_from_container(container: Container, src: pathlib.Path, dst: pathlib.Path):
    """
    Copy a file from a docker container to local

    Args:
        container (Container): Docker container to copy from
        src (Path): Source file path in the container
        dst (Path): Destination file path
    """
    if os.path.dirname(src) == "":
        raise ValueError(f"Source path parent directory cannot be empty!, src: {src}")

    tar_path = dst.with_suffix(".tar")
    stream, _ = container.get_archive(src)
    with open(tar_path, "wb") as tar_file:
        for chunk in stream:
            tar_file.write(chunk)

    with tarfile.open(tar_path, "r") as tar:
        tar.extractall(dst.parent)

    tar_path.unlink()


def exec_run_with_timeout(
    container: Container, cmd, work_dir=None, timeout: int | None = 60
):
    """
    Run a command in a container with a timeout.

    Args:
        container (docker.Container): Container to run the command in.
        cmd (str): Command to run.
        timeout (int): Timeout in seconds.
    """
    # Local variables to store the result of executing the command
    exec_result = ""
    exec_id = None
    exception = None
    timed_out = False

    # Wrapper function to run the command
    def run_command():
        nonlocal exec_result, exec_id, exception
        try:
            exec_id = container.client.api.exec_create(container.id, cmd)["Id"]
            exec_stream = container.client.api.exec_start(
                exec_id, stream=True, workdir=work_dir
            )
            for chunk in exec_stream:
                exec_result += chunk.decode()
        except Exception as e:
            exception = e

    # Start the command in a separate thread
    thread = threading.Thread(target=run_command)
    start_time = time.time()
    thread.start()
    thread.join(timeout)

    if exception:
        raise exception

    # If the thread is still alive, the command timed out
    if thread.is_alive():
        if exec_id is not None:
            exec_pid = container.client.api.exec_inspect(exec_id)["Pid"]
            container.exec_run(f"kill -TERM {exec_pid}", detach=True)
        timed_out = True
    end_time = time.time()
    return exec_result, timed_out, end_time - start_time
