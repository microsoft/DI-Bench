from bigbuild.utils import load_bigbuild_dataset
import pytest

@pytest.mark.skip(reason="dataset not publicly available")
def test_load_buildmark_dataset():
    load_bigbuild_dataset("BigBuildBench/BigBuildBench")
    load_bigbuild_dataset("BigBuildBench/BigBuildBench-Mini")
