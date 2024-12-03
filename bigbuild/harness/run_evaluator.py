import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

from alive_progress import alive_bar
from alive_progress.animations import bar_factory

from bigbuild import RepoInstance
from bigbuild.harness.evaluator import BuildEvaluator
from bigbuild.harness.utils import (
    CacheLevel,
    EvalArgs,
    get_dataset_from_preds,
    get_gold_predictions,
)
from bigbuild.utils.repo import get_repo


def run_instance(args: EvalArgs):
    instance_id = args.instance.instance_id

    # down load repo
    try:
        get_repo(args.instance, args.project_root)
    except Exception:
        print(f"Failed to download repo for {instance_id}")
        return None

    evaluator = BuildEvaluator(args)
    evaluator.run()
    return evaluator.result


def run_instances(
    dataset: List[RepoInstance],
    workspace: Path,
    repo_cache: Path,
    predictions: dict[str, dict],
    concurrency: int,
    cache_level: CacheLevel = "all",
    exec_eval: bool = False,
    text_eval: bool = False,
    timeout: int = 1200,
    resume: bool = False,
    forest: bool = False,
):
    if not repo_cache.exists():
        repo_cache.mkdir(parents=True)
    if not workspace.exists():
        workspace.mkdir(parents=True)
    elif list(workspace.iterdir()) and not resume:
        # backup all previous workspaces
        bak_path = workspace.with_name(workspace.name + "-bak")
        while bak_path.exists():
            bak_path = bak_path.with_name(bak_path.name + "-bak")
        os.rename(workspace, bak_path)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        args = [
            EvalArgs(
                instance=instance,
                project_root=repo_cache / instance.instance_id,
                prediction=predictions[instance.instance_id],
                workspace=workspace / instance.instance_id,
                text_eval=text_eval,
                exec_eval=exec_eval,
                cache_level=cache_level,
                timeout=timeout,
                resume=resume,
                forest=forest,
            )
            for instance in dataset
        ]
        futures = [executor.submit(run_instance, args_) for args_ in args]
        bar_fact = bar_factory(
            "😋",
            tip="🚀",
            background="😈",
            borders=("🍻🤜🤜🤜|", "|🤛🤛🤛🍻"),
            errors=("<- 🫵 🤣", "😅 😅 😅"),
        )
        results = []
        with alive_bar(len(dataset), bar=bar_fact) as bar:
            for future in as_completed(futures):
                results.append(future.result())
                bar()
        return results


def load_predictions(
    path: str, dataset_name_or_path: str
) -> tuple[dict[str, dict], str]:
    if path == "gold":
        print("Using gold predictions - ignoring predictions_path")
        predictions = get_gold_predictions(dataset_name_or_path)
    else:
        with open(path, "r") as f:
            if path.endswith(".json"):
                predictions = json.load(f)
            elif path.endswith(".jsonl"):
                predictions = [json.loads(line) for line in f]
            else:
                raise ValueError('Predictions path must be "gold", .json, or .jsonl')
    model_name = predictions[0].get("model_name_or_path", None)
    return {pred["instance_id"]: pred for pred in predictions}, model_name


def main(
    predictions: str,
    run_id: str,
    dataset_name_or_path: str = "BigBuildBench/BigBuildBench",
    workspace: str = ".cache/eval",
    repo_cache: str = ".cache/repo",
    cache_level: CacheLevel = "all",
    language: str = None,
    instance_ids: List[str] = [],
    concurrency: int = 10,
    exec_eval: bool = True,
    text_eval: bool = True,
    timeout: int = 1200,
    resume: bool = False,
    forest: bool = False,
) -> None:
    """
    Evaluation main entrypoint
    Args:
        predictions (str): Path to predictions file or "gold"
        run_id (str): Run ID
        dataset_name_or_path (str, optional): Dataset name or path. Defaults to "BigBuildBench/BigBuildBench".
        workspace (str, optional): Workspace directory. Defaults to ".cache/workspace".
        repo_cache (str, optional): Repo cache directory. Defaults to ".cache/repo".
        cache_level (CacheLevel, optional): Cache level. Defaults to "all".
        instance_ids (List[str], optional): List of instance ids to evaluate. Defaults to [].
        concurrency (int, optional): Concurrency level. Defaults to 10.
        exec_eval (bool, optional): Evaluate execution metric. Defaults to True.
        text_eval (bool, optional): Evaluate textual metric. Defaults to True.
        timeout (int, optional): Timeout for execution evaluation. Defaults to 1200.
    Returns:
        None
    """
    predictions, model_name = load_predictions(predictions, dataset_name_or_path)
    dataset = get_dataset_from_preds(dataset_name_or_path, instance_ids, predictions)
    workspace: Path = Path(workspace) / model_name / run_id
    repo_cache: Path = Path(repo_cache)
    results = run_instances(
        dataset=dataset,
        workspace=workspace,
        repo_cache=repo_cache,
        predictions=predictions,
        concurrency=concurrency,
        cache_level=cache_level,
        exec_eval=exec_eval,
        text_eval=text_eval,
        timeout=timeout,
        resume=resume,
        forest=forest,
    )
    result_path = workspace / "results.jsonl"
    if result_path.exists():
        bak_path = result_path.with_name(result_path.name + "-bak")
        while bak_path.exists():
            bak_path = bak_path.with_name(bak_path.name + "-bak")
        print(f"Backing up previous results to {bak_path}")
        os.rename(result_path, bak_path)
    print(f"Saving results to {result_path}")
    with open(result_path, "w") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    from fire import Fire

    Fire(main)
