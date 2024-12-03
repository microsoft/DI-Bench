from pathlib import Path

from bigbuild.utils.build_system.python import (
    Pip,
    Poetry,
    SetupTools,
    PEP621Compliant,
)

root = Path(__file__).parent / "data"

def test_python_build_system():
    build_system = Pip(root, ["requirements.txt"])
    parsed = build_system.parse_dependencies()["requirements.txt"]
    assert len(parsed) == 18, len(parsed)

def test_poetry_parse():
    build_system = Poetry(root, ["pyproject.toml"])
    parsed = build_system.parse_dependencies()["pyproject.toml"]
    assert len(parsed) == 3, len(parsed)

def test_pep621_parse():
    build_system = PEP621Compliant(root, ["pyproject.toml"])
    parsed = build_system.parse_dependencies()["pyproject.toml"]
    assert len(parsed) == 15, len(parsed)

def test_setup_cfg_parse():
    build_system = SetupTools(root, ["setup.cfg"])
    parsed = build_system.parse_dependencies()["setup.cfg"]
    assert len(parsed) == 18, len(parsed)

def test_setup_py_parse():
    build_system = SetupTools(root, ["setup.py"])
    parsed = build_system.parse_dependencies()["setup.py"]
    assert len(parsed) == 18, len(parsed)