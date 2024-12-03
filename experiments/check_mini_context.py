from pathlib import Path

from bigbuild import RepoInstance
from bigbuild.inference.builder import Repo, make_builder
from bigbuild.utils import load_bigbuild_dataset


def make_prompt(
    instance: RepoInstance,
    repo_cache: Path,
    model_name: str = "gpt-4o-20240806",
    backend: str = "azure",
):
    project_root = repo_cache / instance.language.lower() / instance.instance_id
    repo = Repo(
        name=instance.instance_id,
        root=project_root,
        language=instance.language.lower(),
        build_files=tuple(instance.build_files),
        env_specs=instance.env_specs,
    )
    build_cache = (
        Path(".cache/experiments/context_distribution")
        / instance.language.lower()
        / instance.instance_id
    )
    build_cache.mkdir(parents=True, exist_ok=True)
    builder = make_builder(
        builder_type="slide",
        repo=repo,
        build_cache=build_cache,
        model_name=model_name,
        backend=backend,
    )
    prompts = list(builder.make_prompt())
    if not len(prompts) == 1:
        print(
            f"{model_name} - {instance.instance_id}: Only one prompt is expected, but got {len(prompts)}"
        )


if __name__ == "__main__":
    dataset = load_bigbuild_dataset("BigBuildBench/BigBuildBench-Mini")
    repo_cache = Path(".cache/repo-mini/")
    backend = "openai"
    models = [
        "Qwen/Qwen2.5-Coder-14B-Instruct",
        "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
        "gpt-4o-20240806",
        "gpt-4o-mini-20240718",
        "gpt-4-0125-preview",
    ]
    for model in models:
        for instance in dataset:
            make_prompt(instance, repo_cache, model, backend)
