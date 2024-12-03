import os

from alive_progress import alive_bar
from github import Auth, Github

from bigbuild.utils import load_bigbuild_dataset

mini_instances = load_bigbuild_dataset("BigBuildBench/BigBuildBench-Mini")
regular_instances = load_bigbuild_dataset("BigBuildBench/BigBuildBench")

instances = mini_instances + regular_instances

ids = [instance.instance_id for instance in instances]
ids = set(ids)

print(f"Total instances: {len(ids)}")

print("Read org repos...")

auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
g = Github(auth=auth)

org_name = "BigBuildBench"
org = g.get_organization(org_name)
org_repos = [repo.name for repo in org.get_repos()]

print(f"Total org repos: {len(org_repos)}")

to_delete = [repo for repo in org_repos if repo not in ids and "_" in repo]

print(f"Total repos to delete: {len(to_delete)}")
print(to_delete[:5])
input("Press Enter to delete...")

with alive_bar(len(to_delete), title="Deleting from org") as bar:
    for repo in to_delete:
        repo = org.get_repo(repo)
        repo.delete()
        bar()
