import logging
import tempfile
from pathlib import Path
import pytest

from bigbuild.utils.ci import run_test_ci

@pytest.mark.skip(reason="runner image not publicly available")
def test_run_test_ci():
    with tempfile.NamedTemporaryFile() as tmp_log_file:
        logger = logging.getLogger("test_logger")
        logger.setLevel(logging.DEBUG)
        file_handler = logging.FileHandler(tmp_log_file.name)
        logger.addHandler(file_handler)

        result, out, _ = run_test_ci(
            run_name="test",
            project_root=Path(__file__).parent / "data" / "dummy_repo",
            command="act",
            logger=logger,
            test_output_file=Path(tmp_log_file.name),
        )
        assert result
        assert "TEST CI SUCCEEDED" in out
