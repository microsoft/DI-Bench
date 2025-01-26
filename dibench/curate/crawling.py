import csv
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle
from pathlib import Path
from typing import Any, Dict, List

import requests
from alive_progress import alive_bar
from dibench.utils.repo import clone_repo, fetch_metadata
from fire import Fire
from github import Auth, Github

HEADERS = {
    "Authorization": "Bearer ",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
BASE_URL = "https://api.github.com/search/repositories"

TOKENS = None
token_lock = threading.Lock()


def rotate_token() -> None:
    """
    Rotate to the next token in the global TOKENS cycle.
    Update HEADERS accordingly. Raise if exhausted (should not happen with cycle).
    """
    global TOKENS, HEADERS
    with token_lock:
        HEADERS["Authorization"] = f"Bearer {next(TOKENS).strip()}"
        print("[INFO] Switched GitHub token")


def do_request(
    url: str,
    method: str = "GET",
    headers: Dict[str, str] = None,
    params: Dict[str, Any] = None,
    max_retries: int = 3,
) -> requests.Response:
    """
    Perform an HTTP request with automatic retry on 403/429 errors.
    If it hits 403/429, rotates token and retries.

    :param url: URL to request
    :param method: HTTP method (GET/POST/etc.)
    :param headers: Request headers
    :param params: Optional query parameters
    :param max_retries: Number of times to attempt a retry after rotate
    :return: requests.Response (raise_for_status already called if successful)
    """
    attempt = 0
    while attempt < max_retries:
        try:
            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, params=params, timeout=30)
            else:
                raise ValueError("This function currently only supports GET.")

            if resp.status_code in (403, 429):
                print(f"[WARNING] {resp.status_code} on {url}. Rotating token...")
                rotate_token()
                attempt += 1
                continue

            resp.raise_for_status()
            return resp

        except requests.exceptions.HTTPError as e:
            if "workflows" in url and "404" in str(e):
                return resp
            print(f"[ERROR] HTTP error: {e}")
            raise
        except Exception as e:
            print(f"[ERROR] Request error: {e}. Rotating token and retrying...")
            rotate_token()
            attempt += 1

    raise RuntimeError(
        f"Failed to fetch {url} after {max_retries} attempts (with token rotation)."
    )


def has_github_actions_workflow(repo_full_name: str) -> bool:
    """
    Checks if a given repo has a GitHub Actions workflow directory.
    Uses do_request with HEADERS for requests.
    Returns True if .github/workflows/ is found, otherwise False.
    """
    url = f"https://api.github.com/repos/{repo_full_name}/contents/.github/workflows"
    try:
        resp = do_request(url, method="GET", headers=HEADERS)
        if resp.status_code == 200:
            return True
    except requests.exceptions.HTTPError as e:
        if "404" in str(e):
            return False
        raise
    return False


def run_repo(
    repo_full_name: str, language: str, cache_dir: Path, output_jsonl: Path
) -> None:
    """
    Fetch metadata from GitHub, clone the repo locally (if not already),
    and append a JSON line with metadata to `output_jsonl`.

    Uses PyGithub with the *current* token from HEADERS.
    """
    token = HEADERS["Authorization"].replace("Bearer ", "")
    auth = Auth.Token(token)
    g = Github(auth=auth)

    instance_id = repo_full_name.replace("/", "_")
    instance = {"instance_id": instance_id, "language": language}

    metadata = fetch_metadata(repo_full_name, g)
    instance["metadata"] = metadata

    clone_path = cache_dir / instance_id
    if not clone_path.exists():
        clone_repo(metadata["full_name"], clone_path)

    with open(output_jsonl, "a", encoding="utf-8") as f:
        f.write(json.dumps(instance, ensure_ascii=False) + "\n")


def process_repo(
    repo_item: Dict[str, Any],
    language: str,
    cache_dir: Path,
    output_jsonl: Path,
    bar,
    stats_dict: Dict[int, Dict[str, int]],
) -> None:
    """
    Worker function to process a single repo:
      - Check if GHA workflow
      - If yes => run_repo
      - Update stats accordingly
      - Advance the global bar
    """
    batch_index = repo_item["batch_index"]
    repo_full_name = repo_item["full_name"]

    try:
        if has_github_actions_workflow(repo_full_name):
            run_repo(repo_full_name, language, cache_dir, output_jsonl)
            with threading.Lock():
                stats_dict[batch_index]["valid"] += 1
    except Exception as e:
        print(f"[ERROR] {repo_full_name}: {str(e)}")

    bar()


def main(
    tokens_file: str = ".cache/TOKENS",
    language: str = "python",
    star_range: List[int] = [100, 300],
    output_dir: str = ".cache",
    cache_dir: str = ".cache/repos",
    concurrency: int = 20,
):
    """
    1) Searches GitHub for repos in `star_range` for `language` (10-star batches).
    2) Check each repo for workflows, if found, dump repo instance into JSONL.

    Args:
        tokens_file: path to a file containing one GitHub token per line.
        language: programming language to search.
        star_range: 2-element [start, end]. Default [100, 300] if None.
        output_dir: directory to write stats and final JSONL.
        cache_dir: where to clone repos locally.
        concurrency: how many threads to use for the actual processing.
    """
    start, end = star_range

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cache_path = Path(cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)

    output_jsonl = output_dir / f"{language}_{start}_{end}.jsonl"
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    global TOKENS
    with open(tokens_file, "r", encoding="utf-8") as f:
        token_lines = [line for line in f if line.strip()]
    if not token_lines:
        raise ValueError("No tokens found in tokens_file.")

    TOKENS = cycle(token_lines)
    rotate_token()  # Initialize the first token

    all_repo_items = []
    batch_list = [(i, min(end, i + 9)) for i in range(start, end, 10)]

    batch_stats = {}
    batch_idx = 0

    for (batch_start, batch_end) in batch_list:
        batch_stats[batch_idx] = {
            "start": batch_start,
            "end": batch_end,
            "all": 0,
            "valid": 0,
        }
        print(f"[INFO] Collecting star range: {batch_start}..{batch_end}")

        page = 1
        while True:
            query = f"language:{language} stars:{batch_start}..{batch_end} size:<100000"
            params = {
                "q": query,
                "per_page": 100,
                "sort": "stars",
                "order": "desc",
                "page": page,
            }

            resp = do_request(BASE_URL, method="GET", headers=HEADERS, params=params)
            data = resp.json()

            items = data.get("items", [])
            if not items:
                break

            for repo in items:
                all_repo_items.append(
                    {"full_name": repo["full_name"], "batch_index": batch_idx}
                )

            batch_stats[batch_idx]["all"] += len(items)

            page += 1
            link = resp.headers.get("link", "")
            if not link or 'rel="next"' not in link:
                break
            if page > 10:
                print("[WARNING] Maximum of 10 pages reached for this batch.")
                break

        batch_idx += 1

    print(f"[INFO] Found a total of {len(all_repo_items)} repos across all batches.")
    with alive_bar(len(all_repo_items), title="Processing repos") as bar:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            future_to_repo = {
                executor.submit(
                    process_repo,
                    repo_item,
                    language,
                    cache_path,
                    output_jsonl,
                    bar,
                    batch_stats,
                ): repo_item
                for repo_item in all_repo_items
            }
            for _ in as_completed(future_to_repo):
                pass

    csv_path = output_dir / f"{language}_stats_{start}_{end}.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["start", "end", "all", "valid"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx in range(len(batch_list)):
            writer.writerow(batch_stats[idx])

    print("[INFO] Done!")
    print(f"      JSONL: {output_jsonl}")
    print(f"      Stats: {csv_path}")

    total_all = sum(b["all"] for b in batch_stats.values())
    total_valid = sum(b["valid"] for b in batch_stats.values())
    print(f"[INFO] GRAND TOTAL: {total_all} repos, {total_valid} with workflows.")


if __name__ == "__main__":
    Fire(main)
