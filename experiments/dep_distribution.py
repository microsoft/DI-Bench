import json
from pathlib import Path

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    import numpy as np

    # draw histogram
    python_result_path = Path(".cache/eval-mini-python/slide/final-bak/results.jsonl")
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

    depcnt = np.array(list(id2dep_count.values()))
    ids = np.array(list(id2dep_count.keys()))
    passes = np.array([id2pass[id] for id in ids])
    precisions = np.array([id2precision[id] for id in ids])
    recalls = np.array([id2recall[id] for id in ids])

    import pandas as pd

    depcnt_binned = pd.qcut(depcnt, q=6, labels=False)
    labels = [
        f"{int(depcnt[depcnt_binned == i].min())}-{int(depcnt[depcnt_binned == i].max())}"
        for i in range(6)
    ]
    frequency = []
    average_pass = []
    average_precision = []
    average_recall = []

    for i in range(6):
        indices = depcnt_binned == i
        frequency.append(indices.sum())
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
    axes[0].set_title("Frequency Dependency Count Range", fontsize=14)
    axes[0].set_xlabel("Dependency Count Range", fontsize=12)
    axes[0].set_ylabel("Frequency", fontsize=12)
    axes[0].grid(axis="y", linestyle="--", alpha=0.7)

    axes[1].plot(
        labels, average_pass, marker="o", color="lightgreen", label="Average Pass"
    )
    axes[1].set_title("Average Pass Per Dependency Count Range", fontsize=14)
    axes[1].set_xlabel("Dependency Count Range", fontsize=12)
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
    axes[2].set_title("Average Precision Per Dependency Count Range", fontsize=14)
    axes[2].set_xlabel("Dependency Count Range", fontsize=12)
    axes[2].set_ylabel("Average Precision", fontsize=12)
    axes[2].grid(axis="y", linestyle="--", alpha=0.7)
    axes[2].legend()

    axes[3].plot(
        labels, average_recall, marker="s", color="gold", label="Average Recall"
    )
    axes[3].set_title("Average Recall Per Dependency Count Range", fontsize=14)
    axes[3].set_xlabel("Dependency Count Range", fontsize=12)
    axes[3].set_ylabel("Average Recall", fontsize=12)

    plt.tight_layout()

    language = "python"

    plt.savefig(f"results/mini_depcnt_{language}.png")
