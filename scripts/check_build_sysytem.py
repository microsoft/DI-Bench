from pathlib import Path

from bigbuild.utils import load_bigbuild_dataset
from bigbuild.utils.build_system import make_build_system
from bigbuild.utils.repo import get_repo

if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--repo_cache", type=str, default=".cache/repo")

    dataset = load_bigbuild_dataset("BigBuildBench/BigBuildBench")

    args = argparser.parse_args()
    cache_root = Path(args.repo_cache)

    for instance in dataset:
        if instance.language.lower() != "csharp":
            continue
        get_repo(instance, cache_root / instance.instance_id)
        try:
            build_system = make_build_system(
                instance.language.lower(),
                cache_root / instance.instance_id,
                instance.build_files,
            )
            build_system.parse_dependencies()
        except Exception as e:
            print(instance.instance_id)
            print(instance.build_files)
            print(e)
        if instance.build_files == ["python/setup.py"]:
            print(instance.instance_id)
            print(build_system.parse_dependencies())
