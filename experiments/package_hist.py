import json
from collections import defaultdict
from pathlib import Path


def correct_predicted_packages(predicted: dict[str, list], oracle: dict[str, list]):
    # predicted and oracle are both dict of build_file_path: list_of_packages
    correct_predicted = defaultdict(int)
    for build_file_path, packages in oracle.items():
        for package in packages:
            if package in predicted.get(build_file_path, []):
                correct_predicted[package] += 1
    return correct_predicted


if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--result-dir", type=str, required=True)
    args = argparser.parse_args()

    # iterate over result dir
    result_dir = Path(args.result_dir)
    results = []
    for subdir in result_dir.iterdir():
        if not subdir.is_dir():
            continue
        eval_result_file = subdir / "eval-result.json"
        results.append(json.loads(eval_result_file.read_text()))

    correct_predicted = defaultdict(int)
    required_packages = defaultdict(int)
    for result in results:
        if not result["detail"]:
            print(f"Failed: {result['instance_id']}")
        pred_packages: dict[str, list] = result["detail"]["predicted"]
        oracle_packages: dict[str, list] = result["detail"]["oracle"]
        for packages in oracle_packages.values():
            for package in packages:
                required_packages[package] += 1
        for package, count in correct_predicted_packages(
            pred_packages, oracle_packages
        ).items():
            correct_predicted[package] += count
    import matplotlib.pyplot as plt
    import numpy as np

    # familiarity:
    # for package required more than 5 times,
    familiarity = sum(
        correct_predicted[package] for package in required_packages.keys()
    ) / sum(required_packages.values())
    print(f"Familiarity: {familiarity}")

    required_packages = dict(
        sorted(required_packages.items(), key=lambda x: x[1], reverse=True)
    )
    # filter out count <= 5
    required_packages = {k: v for k, v in required_packages.items() if v > 3}
    correct_predicted = dict(
        sorted(correct_predicted.items(), key=lambda x: x[1], reverse=True)
    )
    correct_predicted = {
        k: v for k, v in correct_predicted.items() if k in required_packages
    }

    # fig, ax = plt.subplots()
    # ax.bar(np.arange(len(required_packages)), list(required_packages.values()), label='Required')
    # ax.bar(np.arange(len(correct_predicted)), list(correct_predicted.values()), label='Correct')
    # ax.set_xticks(np.arange(len(required_packages)))
    # ax.set_xticklabels(list(required_packages.keys()), rotation=45)
    # ax.yaxis.get_major_locator().set_params(integer=True)
    # ax.legend()
    # render the plot, more beautiful
    fig, ax = plt.subplots()
    bar_width = 0.35
    index = np.arange(len(required_packages))
    ax.bar(index, list(required_packages.values()), bar_width, label="Required")
    ax.bar(
        index + bar_width, list(correct_predicted.values()), bar_width, label="Correct"
    )
    ax.set_xticks(index + bar_width / 2)
    ax.set_xticklabels(list(required_packages.keys()), rotation=45)
    ax.yaxis.get_major_locator().set_params(integer=True)
    # avoid overlap in x-axis
    fig.tight_layout()

    ax.legend()
    plt.savefig("results/package_hist-rust.png")
