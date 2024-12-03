"""
Only support azure/gpt-4o-20240806 for now
"""

import json
from pathlib import Path

import tiktoken

if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--build_trajs_dir", type=str, required=True)

    args = argparser.parse_args()
    build_trajs_dir = Path(args.build_trajs_dir)

    tokenizer = tiktoken.encoding_for_model("gpt-4o-20240806")
    costs = {}
    print("Instance_id,Retrieve,Build")
    for dir in build_trajs_dir.iterdir():
        if not dir.is_dir():
            continue
        trajs_log = dir / "trajs.json"
        if not trajs_log.exists():
            continue
        instance_id = dir.name
        trajs = json.loads(trajs_log.read_text())

        retrieve_trajs = [traj for traj in trajs if traj["purpose"] == "retrieve"]
        build_trajs = [traj for traj in trajs if traj["purpose"] == "build"]

        retrieve_cost = 0
        for traj in retrieve_trajs:
            content = traj["content"]
            token_num = len(tokenizer.encode(content))
            # Note, we calcuate the cost in batch api manner
            if traj["role"] == "user" or traj["role"] == "system":
                # $1.25 / 1M input tokens
                retrieve_cost += token_num * 1.25 / 1e6
            else:
                # $5.00 / 1M output token
                retrieve_cost += token_num * 5.0 / 1e6

        build_cost = 0
        for traj in build_trajs:
            content = traj["content"]
            token_num = len(tokenizer.encode(content))
            if traj["role"] == "user" or traj["role"] == "system":
                # $1.25 / 1M input tokens
                build_cost += token_num * 1.25 / 1e6
            else:
                # $5.00 / 1M output token
                build_cost += token_num * 5.0 / 1e6
        costs[instance_id] = {"retrieve": retrieve_cost, "build": build_cost}
        print(f"{instance_id},{retrieve_cost:.2f},{build_cost:.2f}")

avg_retrieve = 0
avg_build = 0
avg = 0
for instance_id, cost in costs.items():
    avg_retrieve += cost["retrieve"]
    avg_build += cost["build"]
    avg += cost["retrieve"] + cost["build"]
print(
    f"Average\t{avg_retrieve / len(costs):.2f}\t{avg_build / len(costs):.2f}\t{avg / len(costs):.2f}"
)
