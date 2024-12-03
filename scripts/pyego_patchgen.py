import json
from pathlib import Path

from tqdm import tqdm

from bigbuild.inference.builder import Repo
from bigbuild.inference.builder.pigar import patch_gen
from bigbuild.utils import load_bigbuild_dataset

if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--result_dir", type=str)
    args = argparser.parse_args()

    dataset = load_bigbuild_dataset("BigBuildBench/BigBuildBench")

    result_dir = Path(args.result_dir)

    results = []
    for instance in tqdm(dataset):
        if not (result_dir / instance.instance_id).exists():
            print(f"Instance {instance.instance_id} not found in {result_dir}")
            continue

        result: dict = json.loads((result_dir / instance.instance_id).read_text())
        python_packags = result["python_packages"]
        # patch generation
        repo = Repo(
            name=instance.instance_id,
            root=Path(".cache") / "repo" / instance.instance_id,
            build_files=instance.build_files,
            language="python",
            entrypoint=instance.entrypoint_path,
            build_system=instance.build_system,
        )
        requirements = [
            {
                "name": package["name"],
                "specifier": f'=={package["version"]}',
            }
            for package in python_packags
        ]
        analyze_result = {
            "requirements": requirements,
        }
        model_patch = patch_gen(repo, with_version=True, analyze_result=analyze_result)
        results.append(
            {
                "instance_id": instance.instance_id,
                "model_name_or_path": "PyEgo",
                "model_patch": model_patch,
            }
        )
    with open("pyego_results.jsonl", "w") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")
