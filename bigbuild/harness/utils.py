from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal

import tabulate

from bigbuild import RepoInstance
from bigbuild.utils import load_bigbuild_dataset


class EvaluationError(Exception):
    def __init__(self, instance_id, message, logger):
        super().__init__(message)
        self.super_str = super().__str__()
        self.instance_id = instance_id
        self.log_file = logger.log_file
        self.logger = logger

    def __str__(self):
        return (
            f"Evaluation error for {self.instance_id}:\n"
            f"{self.super_str}\n"
            f"Check ({self.log_file}) for more information."
        )


CacheLevel = Literal["result", "log", "all"]


@dataclass(frozen=True)
class EvalArgs:
    instance: RepoInstance
    project_root: Path
    prediction: dict
    workspace: Path
    text_eval: bool
    exec_eval: bool
    cache_level: CacheLevel
    timeout: int
    resume: bool
    forest: bool


def get_gold_predictions(dataset_name_or_path: str) -> list[dict]:
    dataset = load_bigbuild_dataset(dataset_name_or_path)
    return [
        {
            "instance_id": instance.instance_id,
            "model_name_or_path": "gold",
            "model_patch": instance.patch,
        }
        for instance in dataset
    ]


def get_dataset_from_preds(
    dataset_name_or_path: str,
    instance_ids: List[str],
    predictions: dict[str, dict],
) -> List[RepoInstance]:
    dataset = load_bigbuild_dataset(dataset_name_or_path)
    if not instance_ids:
        instance_ids = [instance.instance_id for instance in dataset]
    missing_preds = set(instance_ids) - set(predictions.keys())
    if missing_preds:
        print(f"Warning: Missing predictions for instances: {missing_preds}")

    if set(predictions.keys()) - set(instance.instance_id for instance in dataset):
        print(
            f"""Some prediction IDs not found in dataset!
Missing IDs:
{' '.join(set(predictions.keys()) - set(instance_ids))}"""
        )
    return [
        instance
        for instance in dataset
        if (instance.instance_id in predictions)
        and (instance.instance_id in instance_ids)
    ]


def pretty_print_results(results: list[dict]):
    stats = dict()
    total = len(results)
    stats["total"] = total
    stats["test_passed"] = len(
        [result for result in results if result["exec_metric"] == "pass"]
    )
    missing_exec_metric_instances = [
        result["instance_id"] for result in results if not result["exec_metric"]
    ]
    missing_text_metric_instances = [
        result["instance_id"] for result in results if not result["text_metric"]
    ]
    results = [result for result in results if result["text_metric"]]
    avg_precision_with_version = sum(
        result["text_metric"]["with_version"]["precision"] for result in results
    ) / len(results)
    avg_recall_with_version = sum(
        result["text_metric"]["with_version"]["recall"] for result in results
    ) / len(results)
    avg_f1_with_version = sum(
        result["text_metric"]["with_version"]["f1"] for result in results
    ) / len(results)

    stats["avg_precision_with_version"] = avg_precision_with_version
    stats["avg_recall_with_version"] = avg_recall_with_version
    stats["avg_f1_with_version"] = avg_f1_with_version

    avg_precision_wo_version = sum(
        result["text_metric"]["without_version"]["precision"] for result in results
    ) / (total - len(missing_text_metric_instances))
    avg_recall_wo_version = sum(
        result["text_metric"]["without_version"]["recall"] for result in results
    ) / (total - len(missing_text_metric_instances))
    avg_f1_wo_version = sum(
        result["text_metric"]["without_version"]["f1"] for result in results
    ) / (total - len(missing_text_metric_instances))
    stats["avg_precision_wo_version"] = avg_precision_wo_version
    stats["avg_recall_wo_version"] = avg_recall_wo_version
    stats["avg_f1_wo_version"] = avg_f1_wo_version
    if missing_exec_metric_instances:
        print("=========Missing exec_metric instances=========")
        print("\n".join(missing_exec_metric_instances))
    if missing_text_metric_instances:
        print("=========Missing text_metric instances=========")
        print("\n".join(missing_text_metric_instances))
    print("=========Statics=========")
    print(tabulate.tabulate(stats.items(), headers=["Metric", "Value"]))
