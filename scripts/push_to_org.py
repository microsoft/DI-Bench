if __name__ == "__main__":
    import argparse
    import json
    import os
    import subprocess
    from pathlib import Path

    import requests
    from alive_progress import alive_bar
    from github import Auth, Github

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--jsonl", type=str, required=True)
    argparser.add_argument("--folder", type=str, required=True)
    argparser.add_argument("--ow", action="store_true")

    args = argparser.parse_args()
    with open(args.jsonl, "r") as f:
        instances = [json.loads(line) for line in f]

    print(f"Total instances: {len(instances)}")

    input("Press Enter to push to org...")

    auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
    g = Github(auth=auth)

    org_name = "BigBuildBench"
    org = g.get_organization(org_name)
    org_repos = [repo.name for repo in org.get_repos()]

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Authorization": f'token {os.getenv("GITHUB_TOKEN")}',
    }

    params = {
        "enabled": False,
    }

    with alive_bar(len(instances), title="Pushing to org") as bar:
        for instance in instances:
            repo = None
            try:
                instance_id = instance["instance_id"]
                if instance_id in org_repos:
                    if not args.ow:
                        raise Exception(f"{instance_id} already exists in org")
                    else:
                        repo = org.get_repo(instance_id)
                        repo.delete()
                        print(f"> {instance_id} deleted")

                repo_path = Path(args.folder) / instance_id
                if not repo_path.exists():
                    raise FileNotFoundError(f"Repo path {repo_path} does not exist")

                repo = org.create_repo(instance_id)
                subprocess.run(
                    f"git remote add bbb {repo.clone_url}",
                    shell=True,
                    cwd=repo_path,
                    capture_output=True,
                )

                res = subprocess.run(
                    "git push --all bbb", shell=True, cwd=repo_path, capture_output=True
                )
                if res.returncode != 0:
                    print(res.stderr)
                    raise Exception(
                        f">>>>>>>>>> Failed to push to repo {instance_id} <<<<<<<<<<"
                    )

                print(f"> {instance_id} pushed")

                url = f"https://api.github.com/repos/{org_name}/{instance_id}/actions/permissions"
                response = requests.put(url, headers=headers, json=params)
                if response.status_code == 204:
                    print(f"> {instance_id} disabled actions")
            except Exception as e:
                if repo:
                    repo.delete()
                print(e)
            finally:
                bar()
