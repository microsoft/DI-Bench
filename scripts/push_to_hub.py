# this file push our jsonl file to hub

from datasets import DatasetDict, load_dataset

if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--jsonl_file", type=str, required=True)
    argparser.add_argument("--commit_message", type=str, default="Update dataset")
    argparser.add_argument("--host", type=str, default="BigBuildBench/BigBuildBench")
    args = argparser.parse_args()
    datasets = load_dataset("json", data_files=args.jsonl_file)
    datasets = DatasetDict({"test": datasets["train"]})
    print(datasets)
    print(datasets["test"][0])
    input("Press Enter to push to hub...")
    # add commit message
    datasets.push_to_hub(
        args.host,
        private=True,
        token=True,
        commit_message=args.commit_message,
    )
