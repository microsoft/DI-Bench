import argparse
import json
from pathlib import Path

from termcolor import colored


def cprint(text, color):
    print(colored(text, color))


model_size = {
    "deepseek-ai--DeepSeek-Coder-V2-Lite-Instruct": "2.4B/16B",
    "Qwen--Qwen2.5-Coder-3B-Instruct": "3B",
    "Qwen--Qwen2.5-Coder-14B-Instruct": "14B",
    "Qwen--Qwen2.5-Coder-32B-Instruct": "32B",
    "Qwen--Qwen2.5-Coder-7B-Instruct": "7B",
}


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--result-dir", type=str, required=True)
    argparser.add_argument(
        "--model", type=str, default="meta-llama--Llama-3.1-8B-Instruct"
    )
    argparser.add_argument("--language", type=str, default="csharp")

    args = argparser.parse_args()

    result_dir = Path(args.result_dir) / args.model / args.language

    results = []
    for subdir in result_dir.iterdir():
        if subdir.is_dir():
            result_path = subdir / "eval-result.json"
            if not result_path.exists():
                cprint(f"Result not found: {result_path}", "red")
                continue
            result = json.loads(result_path.read_text())
            results.append(result)
            oracle_package_num = sum(
                len(set(package_list))
                for package_list in result["detail"]["oracle"].values()
            )
            if oracle_package_num == 0:
                cprint(f"Oracle package list is empty: {result_path}", "red")
            tp = result["text"]["name_only"]["TP"]
            fn = result["text"]["name_only"]["FN"]
            if tp + fn != oracle_package_num:
                cprint(
                    f"TP + FN({tp} + {fn}) != oracle package num({oracle_package_num}): {result_path}",
                    "yellow",
                )
    cprint(f"Found {len(results)} results", "green")

    # cprint(f"Found {len(results)} / 100 results, empty result will not be counted", "green")

    calculate = ["text", "exec"]

    pass_rate = sum(result["exec"] == "pass" for result in results) / len(results)
    patch_pass_rate = sum(result["patch-exec"] == "pass" for result in results) / len(
        results
    )

    exact_tp = sum(result["text"]["exact"]["TP"] for result in results)
    exact_fp = sum(result["text"]["exact"]["FP"] for result in results)
    exact_fn = sum(result["text"]["exact"]["FN"] for result in results)
    exact_precision = (
        exact_tp / (exact_tp + exact_fp) if (exact_tp + exact_fp) > 0 else 0
    )
    exact_recall = exact_tp / (exact_tp + exact_fn)
    exact_f1 = (
        2 * exact_precision * exact_recall / (exact_precision + exact_recall)
        if (exact_precision + exact_recall) > 0
        else 0
    )
    # print(f"Pass rate: {pass_rate:.3f}")
    # print("Strict")
    # print(f"  Precision: {exact_precision:.3f}")
    # print(f"  Recall: {exact_recall:.3f}")
    # print(f"  F1: {exact_f1:.3f}")

    name_tp = sum(result["text"]["name_only"]["TP"] for result in results)
    name_fp = sum(result["text"]["name_only"]["FP"] for result in results)
    name_fn = sum(result["text"]["name_only"]["FN"] for result in results)
    name_precision = name_tp / (name_tp + name_fp) if (name_tp + name_fp) > 0 else 0
    name_recall = name_tp / (name_tp + name_fn) if (name_tp + name_fn) > 0 else 0
    name_f1 = (
        2 * name_precision * name_recall / (name_precision + name_recall)
        if (name_precision + name_recall) > 0
        else 0
    )
    # print("Name only")
    # print(f"  Precision: {name_precision:.3f}")
    # print(f"  Recall: {name_recall:.3f}")
    # print(f"  F1: {name_f1:.3f}")

    fake_libs = sum(result["text"].get("fake_libs", 0) for result in results)
    all_predictions = sum(result["text"]["exact"]["TP"] for result in results) + sum(
        result["text"]["exact"]["FP"] for result in results
    )
    fake_rate = fake_libs / all_predictions
    # print(f"Fake rate: {fake_rate:.3f}")
    # Language & Model & Size & Exec & Precision & Recall & F1 & Fake Rate \\
    pass_rate = round(pass_rate * 100, 3)
    name_precision = round(name_precision * 100, 3)
    name_recall = round(name_recall * 100, 3)
    name_f1 = round(name_f1 * 100, 3)
    fake_rate = round(fake_rate * 100, 3)
    model_name = args.model
    if model_name.count("--") >= 1:
        model_name = args.model.split("--")[1]
    print(
        f"{args.language}\n & {model_name} & {model_size.get(args.model, '-')} & {pass_rate:.1f} & {name_precision:.1f} & {name_recall:.1f} & {name_f1:.1f} & {fake_rate:.1f} \\\\"
    )
