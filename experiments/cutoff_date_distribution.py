import datetime
from collections import Counter

import matplotlib.pyplot as plt
from bigbuild.utils import load_bigbuild_dataset


def plot_date_distribution(dates, name):
    """
    绘制一个 datetime.date 数组中每个年月的分布图。

    参数:
        dates (list of datetime.date): 包含日期的数组。
    """
    if not dates:
        print("日期数组为空，无数据可绘制。")
        return

    year_month_counts = Counter((date.year, date.month) for date in dates)

    sorted_counts = sorted(year_month_counts.items())

    labels = [f"{year}-{month:02d}" for (year, month), _ in sorted_counts]
    values = [count for _, count in sorted_counts]

    plt.figure(figsize=(30, 6))
    plt.bar(labels, values, color="skyblue")
    plt.xticks(rotation=45)
    plt.xlabel("Year-Month")
    plt.ylabel("Count")
    plt.title(f"Date Distribution for {name}")
    plt.tight_layout()

    plt.savefig(f"results/{name}.png")


if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--result-dir", type=str)
    instances = load_bigbuild_dataset("BigBuildBench/BigBuildBench-Mini")

    results = []
    created_at_list = []
    updated_at_list = []
    for instance in instances:
        # 只保留年月
        created_at: datetime.date = instance.metadata["created_at"]
        created_at_list.append(created_at)
        updated_at: datetime.date = instance.metadata["updated_at"]
        updated_at_list.append(updated_at)

    plot_date_distribution(created_at_list, "date_created_at")
    plot_date_distribution(updated_at_list, "date_updated_at")
