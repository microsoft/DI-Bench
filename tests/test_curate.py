from pathlib import Path
import pytest
from bigbuild.curate.curator import make_curator

@pytest.mark.skip(reason="local only")
def test_builder():
    instance_dict = {
        "instance_id": "test",
        "metadata": {"repo_name": "test"},
        "language": "Python",
        "act_command": "foo",
        "ci_file": "foo",
        "patch": "foo",
        "build_files": ["foo"],
        "entrypoint_path": "foo",
        "build_system": "foo",
    }
    curator = make_curator(instance_dict, Path("."))
    assert curator.to_dict() == instance_dict
