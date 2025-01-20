import json
from collections import defaultdict
from itertools import chain
from pathlib import Path

if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--result-dir", type=str, required=True)
    argparser.add_argument("--package", type=str, default="numpy")
    # set shortcut -s
    argparser.add_argument("-s", "--show-result-path", action="store_true")
    args = argparser.parse_args()

    # iterate over result dir
    result_dir = Path(args.result_dir)
    results = {}
    for subdir in result_dir.iterdir():
        if not subdir.is_dir():
            continue
        eval_result_file = subdir / "eval-result.json"
        results[eval_result_file] = json.loads(eval_result_file.read_text())

    for key, result in results.items():
        oracle: dict = result["detail"]["oracle"]
        oracle_packages = list(chain.from_iterable(oracle.values()))
        model: dict = result["detail"]["predicted"]
        model_packages = list(chain.from_iterable(model.values()))
        if args.package in oracle_packages and args.package not in model_packages:
            if args.show_result_path:
                print(key, end=" ")
            else:
                print(key.parent.name, end=" ")
            if result["exec"] == "pass":
                print("safe omit")
            else:
                print("possibly unsafe omit")

    oracle_frequency = defaultdict(int)
    omit_count = defaultdict(int)
    predicted_frequency = defaultdict(int)
    useless_count = defaultdict(int)
    for key, result in results.items():
        oracle: dict = result["detail"]["oracle"]
        oracle_packages = list(chain.from_iterable(oracle.values()))
        model: dict = result["detail"]["predicted"]
        model_packages = list(chain.from_iterable(model.values()))
        for package in oracle_packages:
            oracle_frequency[package] += 1
            if package not in model_packages:
                omit_count[package] += 1
        for package in model_packages:
            predicted_frequency[package] += 1
            if package not in oracle_packages:
                useless_count[package] += 1

    # draw four histograms
    # 1. omit count distribution
    # 2. useless count distribution
    # 3. omit count / oracle frequency distribution
    # 4. useless count / oracle frequency distribution

    import matplotlib.pyplot as plt

    omit_count = sorted(omit_count.items(), key=lambda x: x[1], reverse=True)
    useless_count = sorted(useless_count.items(), key=lambda x: x[1], reverse=True)

    # for **_count, filter out value with count == 1
    omit_count = [x for x in omit_count if x[1] > 1]
    useless_count = [x for x in useless_count if x[1] > 1]

    omit_frequency = {
        package: count / oracle_frequency[package] for package, count in omit_count
    }
    useless_frequency = {
        package: count / predicted_frequency[package]
        for package, count in useless_count
    }
    omit_frequency = sorted(omit_frequency.items(), key=lambda x: x[1], reverse=True)
    useless_frequency = sorted(
        useless_frequency.items(), key=lambda x: x[1], reverse=True
    )

    # 设置主题风格
    # plt.style.use("seaborn-vibrant")

    # 创建一个图形对象
    fig, axes = plt.subplots(2, 2, figsize=(24, 10))
    fig.suptitle("Textual Analysis", fontsize=16, fontweight="bold")

    # 子图1: Omit Count Distribution
    axes[0, 0].bar(
        [x[0] for x in omit_count],
        [x[1] for x in omit_count],
        color="skyblue",
        edgecolor="black",
    )
    axes[0, 0].set_title("Not In Predicted Count Distribution", fontsize=14)
    axes[0, 0].set_xlabel("Package", fontsize=12)
    axes[0, 0].set_ylabel("Omit Count", fontsize=12)
    axes[0, 0].grid(axis="y", linestyle="--", alpha=0.7)
    axes[0, 0].tick_params(axis="x", rotation=60)

    # 子图2: Useless Count Distribution
    axes[0, 1].bar(
        [x[0] for x in useless_count],
        [x[1] for x in useless_count],
        color="lightcoral",
        edgecolor="black",
    )
    axes[0, 1].set_title("Not In Oracle Count Distribution", fontsize=14)
    axes[0, 1].set_xlabel("Package", fontsize=12)
    axes[0, 1].set_ylabel("Useless Count", fontsize=12)
    axes[0, 1].grid(axis="y", linestyle="--", alpha=0.7)
    axes[0, 1].tick_params(axis="x", rotation=60)

    # 子图3: Omit Frequency Distribution
    axes[1, 0].bar(
        [x[0] for x in omit_frequency],
        [x[1] for x in omit_frequency],
        color="mediumseagreen",
        edgecolor="black",
    )
    axes[1, 0].set_title("Not In Predicted Frequency Distribution", fontsize=14)
    axes[1, 0].set_xlabel("Package", fontsize=12)
    axes[1, 0].set_ylabel("Omit Frequency", fontsize=12)
    axes[1, 0].grid(axis="y", linestyle="--", alpha=0.7)
    axes[1, 0].tick_params(axis="x", rotation=60)

    # 子图4: Useless Frequency Distribution
    axes[1, 1].bar(
        [x[0] for x in useless_frequency],
        [x[1] for x in useless_frequency],
        color="gold",
        edgecolor="black",
    )
    axes[1, 1].set_title("Not In Oracle Frequency Distribution", fontsize=14)
    axes[1, 1].set_xlabel("Package", fontsize=12)
    axes[1, 1].set_ylabel("Useless Frequency", fontsize=12)
    axes[1, 1].grid(axis="y", linestyle="--", alpha=0.7)
    axes[1, 1].tick_params(axis="x", rotation=60)

    # 自动调整布局
    plt.tight_layout(rect=[0, 0, 1, 0.95])  # 为标题留出空间
    plt.savefig("results/package_omit_cases.png", dpi=300)  # 高分辨率保存
    plt.close()
