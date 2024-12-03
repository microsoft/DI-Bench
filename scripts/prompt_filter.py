import json
from dataclasses import asdict
from pathlib import Path

from alive_progress import alive_bar
from fire import Fire

from bigbuild import RepoInstance
from bigbuild.inference.builder import Repo, make_builder


def count_prompt(
    instance: RepoInstance,
    root: Path,
    model_name: str = "gpt-4o-20240806",
    backend: str = "azure",
):
    repo = Repo(
        name=instance.instance_id,
        root=root,
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
    prompt = list(builder.make_prompt())[0]
    return builder.engine.count_tokens(prompt)


def main(
    input_jsonl: str,
    instances_dir: str,
    regular_jsonl: str,
    big_jsonl: str,
):
    with open(input_jsonl, "r") as f:
        dataset = [json.loads(line) for line in f]
    instances = [RepoInstance(**instance) for instance in dataset]

    threshold = 120_000

    models = [
        "deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct",
        "Qwen/Qwen2.5-Coder-14B-Instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
        # "gpt-4o-20240806",
        # "gpt-4o-mini-20240718",
        # "gpt-4-0125-preview",
    ]

    with alive_bar(len(instances)) as bar:
        for instance in instances:
            root = Path(instances_dir) / instance.instance_id
            regular = True
            for model in models:
                prompt_len = count_prompt(instance, root, model, "openai")
                if prompt_len > threshold:
                    print(f"{instance.instance_id} has {prompt_len} tokens for {model}")
                    regular = False
                    break
            if regular:
                with open(regular_jsonl, "a") as f:
                    f.write(json.dumps(asdict(instance)) + "\n")
            else:
                with open(big_jsonl, "a") as f:
                    f.write(json.dumps(asdict(instance)) + "\n")
            bar()


if __name__ == "__main__":
    Fire(main)
