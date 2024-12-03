import json
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Literal

from alive_progress import alive_bar
from alive_progress.animations import bar_factory

from bigbuild.inference.builder import Repo, make_builder
from bigbuild.utils import load_bigbuild_dataset
from bigbuild.utils.repo import get_repo


def build(
    builder_type: str,
    repo: Repo,
    build_cache: Path,
    model_name: str,
    backend: str,
    use_cache: bool,
    max_code_context: int,
    max_new_tokens: int,
    base_url: str | None = None,
    tensor_parallel_size: int = 1,
    trust_remote_code: bool = False,
    attn_implementation=None,
    check_context: bool = False,
):
    try:
        build_cache.mkdir(parents=True, exist_ok=True)
        builder = make_builder(
            builder_type=builder_type,
            repo=repo,
            build_cache=build_cache,
            model_name=model_name,
            backend=backend,
            resume=use_cache,
            max_code_context=max_code_context,
            max_new_tokens=max_new_tokens,
            base_url=base_url,
            tensor_parallel_size=tensor_parallel_size,
            trust_remote_code=trust_remote_code,
            attn_implementation=attn_implementation,
            check_context=check_context,
        )
        return repo.name, builder.patchgen()
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(f"Failed to build {repo.name}: {e}")
        return repo.name, str(e)


def main(
    run_id: str,
    builder_type: Literal["slide"] = "slide",
    dataset_name_or_path: str = "BigBuildBench/BigBuildBench",
    repo_cache: str = ".cache/repo/",
    resume: bool = True,
    model_name: str = "gpt-4o-20240806",
    backend: str = "azure",
    max_code_context: int = 1024 * 128,
    max_new_tokens: int = 1024 * 8,
    base_url: str | None = None,
    tensor_parallel_size: int = 1,
    trust_remote_code: bool = False,
    attn_implementation=None,
    build_cache: str = ".cache/build/",
    n_workers: int = 4,
    language: str = None,
):
    repo_cache = Path(repo_cache)
    build_cache: Path = Path(build_cache)
    build_cache = build_cache / builder_type / run_id / model_name
    dataset = load_bigbuild_dataset(dataset_name_or_path)
    if language:
        if language.lower() not in ["python", "typescript", "rust", "csharp"]:
            raise ValueError(f"Unsupported language: {language}")
        dataset = [
            instance
            for instance in dataset
            if instance.language.lower() == language.lower()
        ]
        build_cache = build_cache / language
        repo_cache = repo_cache / language
    dataset = sorted(dataset, key=lambda x: x.instance_id)
    results = []
    if not resume and build_cache.exists():
        from bigbuild.utils import backup_dir

        backup_dir(build_cache)

    if not build_cache.exists():
        build_cache.mkdir(parents=True, exist_ok=True)
    with open(build_cache / "config.json", "w") as f:
        json.dump(
            dict(
                run_id=run_id,
                builder_type=builder_type,
                dataset_name_or_path=dataset_name_or_path,
                repo_cache=str(repo_cache),
                resume=resume,
                model_name=model_name,
                backend=backend,
                max_code_context=max_code_context,
                max_new_tokens=max_new_tokens,
                base_url=base_url,
                tensor_parallel_size=tensor_parallel_size,
                trust_remote_code=trust_remote_code,
                attn_implementation=attn_implementation,
                build_cache=str(build_cache),
                n_workers=n_workers,
                language=language,
            ),
            f,
            indent=2,
        )
    model_name_or_path = builder_type + "-" + model_name
    with ProcessPoolExecutor(n_workers) as executor:
        futures = []
        for instance in dataset:
            cur_build_cache = build_cache / instance.instance_id
            project_root = repo_cache / instance.instance_id
            try:
                get_repo(instance, project_root)
            except Exception as e:
                print(f"Failed to get repo {instance.instance_id}: {e}")
                continue
            repo = Repo(
                name=instance.instance_id,
                root=project_root,
                language=instance.language.lower(),
                build_files=tuple(instance.build_files),
                env_specs=instance.env_specs,
            )
            futures.append(
                executor.submit(
                    build,
                    builder_type,
                    repo,
                    cur_build_cache,
                    model_name,
                    backend,
                    resume,
                    max_code_context,
                    max_new_tokens,
                    base_url,
                    tensor_parallel_size,
                    trust_remote_code,
                    attn_implementation,
                )
            )

        with alive_bar(
            len(futures), bar=bar_factory("🔥", background="💸"), title="B^3"
        ) as bar:
            for future in as_completed(futures):
                instance_id, patch = future.result()
                result = dict(
                    instance_id=instance_id,
                    model_name_or_path=model_name_or_path,
                    model_patch=patch,
                )
                results.append(result)
                bar()
    results_path = build_cache / "results.jsonl"
    with open(results_path, "w") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    import fire

    fire.Fire(main)
