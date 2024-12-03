import os
import shutil
import subprocess
import tempfile
import warnings
from pathlib import Path

from alive_progress import alive_bar
from fire import Fire
from transformers import AutoTokenizer

from bigbuild import RepoInstance
from bigbuild.utils import load_bigbuild_dataset
from bigbuild.utils.build_system import make_build_system
from bigbuild.utils.repo import lang2suffix

warnings.simplefilter("ignore", FutureWarning)


def loc(file_path):
    non_empty_lines = 0
    try:
        with open(file_path, "r") as file:
            for line in file:
                if line.strip():
                    non_empty_lines += 1
    except Exception:
        pass

    return non_empty_lines


def get_count(folder: Path, language: str, tokenizer: AutoTokenizer):
    suffix = lang2suffix[language]
    count = 0
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(tuple(suffix)):
                with open(os.path.join(root, file), "r") as f:
                    count += len(tokenizer.tokenize(f.read()))
    return count


def stats(
    instance: RepoInstance, folder: Path, language: str, tokenizer: AutoTokenizer
):
    result = {}
    if language not in lang2suffix:
        raise ValueError(f"Unsupported language: {language}")
    suffix = lang2suffix[language]
    token_count = 0
    file_count = 0
    loc_count = 0
    for root, _, files in os.walk(folder):
        for file in files:
            if file.endswith(tuple(suffix)):
                file_count += 1
                loc_count += loc(os.path.join(root, file))
                with open(os.path.join(root, file), "r") as f:
                    token_count += len(tokenizer.encode(f.read()))

    result["file_count"] = file_count
    result["token_count"] = token_count
    result["loc_count"] = loc_count

    dep_count = 0

    # temp folder
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            shutil.copytree(folder, Path(tmp_dir) / instance.instance_id, symlinks=True)
            instance_id = instance.instance_id
            patch_path = Path(tmp_dir) / instance_id / "patch.diff"
            patch_path.write_text(instance.patch)

            # apply patch
            output = subprocess.run(
                ["git", "apply", str(patch_path)],
                cwd=str(Path(tmp_dir) / instance_id),
                capture_output=True,
                text=True,
            )

            if output.returncode != 0:
                output = subprocess.run(
                    ["patch", "--batch", "--fuzz=5", "-p1", "-i", str(patch_path)],
                    cwd=str(Path(tmp_dir) / instance_id),
                    capture_output=True,
                    text=True,
                )
                if output.returncode != 0:
                    raise Exception("Patch failed")

            build_files = instance.build_files
            build_system = make_build_system(
                language, Path(tmp_dir) / instance.instance_id, build_files
            )
            dep_dict = build_system.parse_dependencies()
            for deps in dep_dict.values():
                dep_count += len(deps)
    except Exception as e:
        print(e)

    result["dep_count"] = dep_count
    return result


def main(
    dataset: str = "BigBuildBench/BigBuildBench",
    language: str = None,
):
    tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.2-3B")

    cache_repo = Path(os.getenv("CACHE_DIR", ".cache")) / "repo"
    instances = load_bigbuild_dataset(dataset)
    if language:
        instances = [i for i in instances if i.language.lower() == language.lower()]

    results = []

    with alive_bar(len(instances)) as bar:
        for instance in instances:
            try:
                lang = instance.language.lower()
                folder = Path(cache_repo) / instance.instance_id
                result = stats(instance, folder, lang, tokenizer)
                results.append(result)
            except Exception as e:
                print(f"Error: {instance.instance_id} === {e}")
            bar()

    print(f"Summary of language: {language if language else 'all'}")
    print("-" * 50)
    print("Total instances:", len(results))
    print(
        f"Files:\n  - Mean: {sum([r['file_count'] for r in results]) / len(results)}\n  - Max: {max([r['file_count'] for r in results])}"
    )
    print(
        f"LoC:\n  - Mean: {sum([r['loc_count'] for r in results]) / len(results)}\n  - Max: {max([r['loc_count'] for r in results])}"
    )
    print(
        f"Tokens:\n  - Mean: {sum([r['token_count'] for r in results]) / len(results)}\n  - Max: {max([r['token_count'] for r in results])}"
    )
    print(
        f"Dependencies:\n  - Mean: {sum([r['dep_count'] for r in results]) / len(results)}\n  - Max: {max([r['dep_count'] for r in results])}"
    )


if __name__ == "__main__":
    Fire(main)
