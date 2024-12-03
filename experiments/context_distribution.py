import json
from pathlib import Path

import tempdir
from tqdm import tqdm

from bigbuild import RepoInstance
from bigbuild.inference.builder import Repo, make_builder
from bigbuild.utils import load_bigbuild_dataset
from bigbuild.utils.llm.provider.request import construct_message_list


def instance_input_length(
    instance: RepoInstance, repo_cache: Path, model_name: str, build_cache: Path
):
    project_root = repo_cache / instance.language.lower() / instance.instance_id
    repo = Repo(
        name=instance.instance_id,
        root=project_root,
        language=instance.language.lower(),
        build_files=tuple(instance.build_files),
        env_specs=instance.env_specs,
    )
    builder = make_builder(
        builder_type="slide",
        repo=repo,
        build_cache=build_cache,
        model_name=model_name,
        backend=backend,
    )
    prompts = list(builder.make_prompt())
    system_msg, prompt = prompts[0]
    prompt_tokens = builder.engine.tokenizer.apply_chat_template(
        construct_message_list(prompt, system_msg),
        return_tensors="pt",
        add_generation_prompt=True,
    )
    input_length = prompt_tokens.size(-1)
    if input_length > 120_000:
        print("Input length exceeds 120k tokens")
    return input_length


if __name__ == "__main__":
    dataset = load_bigbuild_dataset("BigBuildBench/BigBuildBench-Mini")
    repo_cache = Path(".cache/repo-mini/")
    backend = "openai"
    # for model in models:
    # models = [
    #     "Qwen/Qwen2.5-Coder-14B-Instruct", "DeepSeek-Coder-V2-Lite-instruct", "Lamma-3.1-8b-instruct",
    #     "gpt-4o-20240806", "gpt-4o-mini-20240718", "gpt-4-0125-preview"
    # ]
    id2context = {}
    result_path = Path("results/mini_contexts.json")
    language = "python"
    if result_path.exists():
        id2context = json.loads(result_path.read_text())
    with tempdir.TempDir() as tmpdir:
        for instance in tqdm(dataset):
            if instance.language.lower() != language:
                if instance.instance_id in id2context:
                    del id2context[instance.instance_id]
                continue
            if instance.instance_id in id2context:
                continue
            input_length = instance_input_length(
                instance, repo_cache, "meta-llama/Llama-3.1-8B-Instruct", Path(tmpdir)
            )
            id2context[instance.instance_id] = input_length
    with open("results/mini_contexts.json", "w") as f:
        json.dump(id2context, f, indent=2)
    exit()

    import matplotlib.pyplot as plt
    import numpy as np

    # draw histogram
    data = np.array(list(id2context.values()))
    bins = [1e3, 1e4, 2 * 1e4, 3 * 1e4, 4 * 1e4, 5 * 1e4, 6 * 1e4, np.inf]
    labels = ["1k-10k", "10k-20k", "20k-30k", "30k-40k", "40k-50k", "50k-60k", "60k+"]
    frequency, _ = np.histogram(data, bins=bins)

    python_result_path = Path(".cache/eval-mini-python/slide/final/results.jsonl")
    python_eval_results = [
        json.loads(line) for line in python_result_path.read_text().splitlines()
    ]
    id2pass = {
        result["instance_id"]: result["exec"] == "pass"
        for result in python_eval_results
    }
    id2precision = {}
    id2recall = {}
    id2dep_count = {}
    for result in python_eval_results:
        tp, fp, fn = (
            result["text"]["name_only"]["TP"],
            result["text"]["name_only"]["FP"],
            result["text"]["name_only"]["FN"],
        )
        precision = tp / (tp + fp) if tp + fp > 0 else 0
        recall = tp / (tp + fn) if tp + fn > 0 else 0
        id2precision[result["instance_id"]] = precision
        id2recall[result["instance_id"]] = recall
        id2dep_count[result["instance_id"]] = tp + fn

    ids = np.array(list(id2context.keys()))
    context = np.array(list(id2context.values()))
    passes = np.array([id2pass[id] for id in ids])
    precisions = np.array([id2precision[id] for id in ids])
    recalls = np.array([id2recall[id] for id in ids])

    average_pass = []
    average_precision = []
    average_recall = []
    for i in range(len(bins) - 1):
        indices = (context >= bins[i]) & (context < bins[i + 1])
        if indices.any():
            average_pass.append(passes[indices].mean())
            average_precision.append(precisions[indices].mean())
            average_recall.append(recalls[indices].mean())
        else:
            average_pass.append(0)
            average_precision.append(0)
            average_recall.append(0)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    axes[0].bar(labels, frequency, color="skyblue", edgecolor="black", alpha=0.8)
    axes[0].set_title("Frequency Per Context Range", fontsize=14)
    axes[0].set_xlabel("Context Range", fontsize=12)
    axes[0].set_ylabel("Frequency", fontsize=12)
    axes[0].grid(axis="y", linestyle="--", alpha=0.7)

    axes[1].plot(
        labels, average_pass, marker="o", color="lightgreen", label="Average Pass"
    )
    axes[1].set_title("Average Pass Per Context Range", fontsize=14)
    axes[1].set_xlabel("Context Range", fontsize=12)
    axes[1].set_ylabel("Average Pass", fontsize=12)
    axes[1].grid(axis="y", linestyle="--", alpha=0.7)
    axes[1].legend()

    axes[2].plot(
        labels,
        average_precision,
        marker="x",
        color="lightcoral",
        label="Average Precision",
    )
    axes[2].set_title("Average Precision Per Context Range", fontsize=14)
    axes[2].set_xlabel("Context Range", fontsize=12)
    axes[2].set_ylabel("Average Precision", fontsize=12)
    axes[2].grid(axis="y", linestyle="--", alpha=0.7)
    axes[2].legend()

    axes[3].plot(
        labels, average_recall, marker="s", color="gold", label="Average Recall"
    )
    axes[3].set_title("Average Recall Per Context Range", fontsize=14)
    axes[3].set_xlabel("Context Range", fontsize=12)
    axes[3].set_ylabel("Average Recall", fontsize=12)

    plt.tight_layout()

    plt.savefig(f"results/mini_contexts_{language}.png")
