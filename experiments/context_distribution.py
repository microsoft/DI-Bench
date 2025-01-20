import json
from pathlib import Path

import tiktoken
from bigbuild.utils import load_bigbuild_dataset

if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--prompt-file", type=str, default="results/bigbuild-prompts.jsonl"
    )
    argparser.add_argument("--result-root", type=str, default="results/gpt-4o-20240806")
    args = argparser.parse_args()

    prompt_file = Path(args.prompt_file)
    prompts = [json.loads(line) for line in prompt_file.read_text().splitlines()]
    tokenizer = tiktoken.encoding_for_model("gpt-4o-20240806")

    id2prompt = {}
    id2context = {}
    for prompt in prompts:
        id2prompt[prompt["instance_id"]] = prompt["prompts"][0]["content"]

    id2pass = {}
    id2precision = {}
    id2recall = {}
    id2dep_count = {}
    dataset = load_bigbuild_dataset("BigBuildBench/BigBuildBench-Mini")
    result_root = Path(args.result_root)
    for instance in dataset:
        prompt = id2prompt[instance.instance_id]
        context = len(tokenizer.encode(prompt, disallowed_special=()))
        id2context[instance.instance_id] = context
        result_file = (
            result_root
            / instance.language.lower()
            / instance.instance_id
            / "eval-result.json"
        )
        eval_result = json.loads(result_file.read_text())
        id2pass[instance.instance_id] = eval_result["exec"] == "pass"
        tp, fp, fn = (
            eval_result["text"]["name_only"]["TP"],
            eval_result["text"]["name_only"]["FP"],
            eval_result["text"]["name_only"]["FN"],
        )
        precision = tp / (tp + fp) if tp + fp > 0 else 0
        recall = tp / (tp + fn) if tp + fn > 0 else 0
        id2precision[instance.instance_id] = precision
        id2recall[instance.instance_id] = recall
        id2dep_count[instance.instance_id] = tp + fn

    import matplotlib.pyplot as plt
    import numpy as np

    # draw histogram
    data = np.array(list(id2context.values()))
    bins = [1e3, 1e4, 2 * 1e4, 3 * 1e4, 4 * 1e4, 5 * 1e4, 6 * 1e4, np.inf]
    labels = ["1k-10k", "10k-20k", "20k-30k", "30k-40k", "40k-50k", "50k-60k", "60k+"]
    frequency, _ = np.histogram(data, bins=bins)

    id2precision = {}
    id2recall = {}
    id2dep_count = {}
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

    plt.savefig("results/mini_contexts.png")
