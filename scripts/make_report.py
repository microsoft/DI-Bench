import argparse
import json

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--results", type=str, required=True)

    args = argparser.parse_args()
    results_path = args.results

    with open(results_path, "r") as f:
        results = [json.loads(line) for line in f]

    pass_rate = sum(result["exec"] == "pass" for result in results) / len(results)

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
    print(f"Pass rate: {pass_rate:.3f}")
    print("Strict")
    print(f"  Precision: {exact_precision:.3f}")
    print(f"  Recall: {exact_recall:.3f}")
    print(f"  F1: {exact_f1:.3f}")

    name_tp = sum(result["text"]["name_only"]["TP"] for result in results)
    name_fp = sum(result["text"]["name_only"]["FP"] for result in results)
    name_fn = sum(result["text"]["name_only"]["FN"] for result in results)
    name_precision = name_tp / (name_tp + name_fp)
    name_recall = name_tp / (name_tp + name_fn)
    name_f1 = 2 * name_precision * name_recall / (name_precision + name_recall)
    print("Name only")
    print(f"  Precision: {name_precision:.3f}")
    print(f"  Recall: {name_recall:.3f}")
    print(f"  F1: {name_f1:.3f}")

    fake_libs = sum(result["text"].get("fake_libs", 0) for result in results)
    all_predictions = sum(result["text"]["exact"]["TP"] for result in results) + sum(
        result["text"]["exact"]["FP"] for result in results
    )
    fake_rate = fake_libs / all_predictions
    print(f"Fake rate: {fake_rate:.3f}")
