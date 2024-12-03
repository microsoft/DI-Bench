import csv
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

import requests
from alive_progress import alive_bar
from fire import Fire

HEADERS = {
    "Authorization": "Bearer ",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
BASE_URL = "https://api.github.com/search/repositories"
LIMIT = 5000 - 200

TOKENS = None
count = 0

token_lock = threading.Lock()
count_lock = threading.Lock()


def change_token():
    global TOKENS, HEADERS
    with token_lock:
        if TOKENS:
            HEADERS["Authorization"] = f"Bearer {TOKENS.pop(0).strip()}"
            print("Token changed")
        else:
            raise Exception("All tokens exhausted")


def check_workflows_exists(repo_full_name, bar):
    global count, TOKENS
    url = f"https://api.github.com/repos/{repo_full_name}/contents/.github/workflows"
    response = requests.get(url, headers=HEADERS)
    with count_lock:
        bar()
        count += 1
        if count % LIMIT == 0:
            change_token()

    if response.status_code == 200:
        return True
    elif response.status_code == 404:
        return False
    elif response.status_code == 403 or response.status_code == 429:
        print(response.status_code)
        ret_code = response.headers.get("x-ratelimit-remaining")
        if ret_code == "0":
            print("Rate limit exceeded")
        return False
    else:
        response.raise_for_status()


def main(
    tokens_file: str = ".cache/TOKENS",
    language: str = "csharp",
    star_range: List[int] = [100, 1000],
    output_dir: str = ".cache",
):
    global TOKENS
    global HEADERS

    with open(tokens_file, "r") as f:
        TOKENS = f.readlines()

    change_token()

    all_repos = []
    batch_stats = []

    start = star_range[0]
    end = star_range[1]
    batch_list = [(i, min(end, i + 9)) for i in range(start, end, 10)]
    try:
        with alive_bar() as bar:
            for batch in batch_list:
                print(f"Processing: {batch[0]}..{batch[1]}")
                query = f"language:{language} stars:{batch[0]}..{batch[1]} size:<100000"
                params = {
                    "q": query,
                    "per_page": 100,
                    "sort": "stars",
                    "order": "desc",
                }
                page = 1
                stat = {"start": batch[0], "end": batch[1], "all": 0, "valid": 0}

                while True:
                    params = {**params, "page": page}
                    response = requests.get(BASE_URL, headers=HEADERS, params=params)
                    response.raise_for_status()
                    data = response.json()
                    link = response.headers.get("link")

                    if not data["items"]:
                        break

                    stat["all"] += len(data["items"])

                    with ThreadPoolExecutor(max_workers=10) as executor:
                        future_to_repo = {
                            executor.submit(
                                check_workflows_exists, repo["full_name"], bar
                            ): repo["full_name"]
                            for repo in data["items"]
                        }
                        for future in as_completed(future_to_repo):
                            repo_name = future_to_repo[future]
                            if future.result():
                                stat["valid"] += 1
                                all_repos.append(repo_name)

                    page += 1
                    if page > 10:
                        print("WARNING: Max page reached")
                    if not link or 'rel="next"' not in link:
                        break

                batch_stats.append(stat)

    except Exception as e:
        print(e)
    finally:
        import os

        with open(
            os.path.join(output_dir, f"{language}_repos_{start}_{end}.txt"), "w"
        ) as f:
            f.write("\n".join(all_repos))

        plt = plot(batch_stats)
        plt.savefig(os.path.join(output_dir, f"{language}_repos_{start}_{end}.png"))

        with open(
            os.path.join(output_dir, f"{language}_stats_{start}_{end}.csv"), "w"
        ) as f:
            writer = csv.DictWriter(f, fieldnames=["start", "end", "all", "valid"])
            writer.writeheader()
            writer.writerows(batch_stats)


def plot(batch_stats):
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_context("notebook")
    sns.set_style("whitegrid")

    batches = [f"{stat['start']}-{stat['end']}" for stat in batch_stats]
    all_repos = [stat["all"] for stat in batch_stats]
    valid_repos = [stat["valid"] for stat in batch_stats]

    all_repo_count = sum(all_repos)
    valid_repos_count = sum(valid_repos)

    print(f"Total Repositories: {all_repo_count}")
    print(f"Valid Repositories: {valid_repos_count}")

    plt.figure(figsize=(5 + len(batches) * 0.3, 6))
    ax = sns.barplot(
        x=batches, y=all_repos, color="lightblue", label="Total Repositories"
    )
    ax = sns.barplot(
        x=batches, y=valid_repos, color="orange", label="Valid Repositories"
    )

    ax.set_xlabel("Star Range (per batch)")
    ax.set_ylabel("Number of Repositories")
    ax.set_title("Repository Statistics by Star Range")

    plt.xticks(rotation=45, ha="right")
    ax.legend()
    plt.grid(True, which="both", linestyle="--", linewidth=0.5)

    return plt


if __name__ == "__main__":
    Fire(main)
