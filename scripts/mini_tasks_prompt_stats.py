import pathlib

from transformers import AutoTokenizer

from bigbuild.inference.builder import Repo
from bigbuild.inference.run_mini_builder import make_prompt
from bigbuild.utils import load_bigbuild_dataset

if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser()
    argparser.add_argument("--repo_cache", type=str, default=".cache/repo-mini/")
    args = argparser.parse_args()

    repo_cache = pathlib.Path(args.repo_cache)

    tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-2-7b-hf")

    dataset = load_bigbuild_dataset("BigBuildBench/BigBuildBench-Mini")
    for data in dataset:
        repo = Repo(
            name=data.instance_id,
            root=repo_cache / data.instance_id,
            language=data.language,
            build_files=data.build_files,
            env_specs=data.env_specs,
        )
        sys_prompt, prompt = make_prompt(repo)
        token_count = len(tokenizer.tokenize(prompt))
        print(f"{data.instance_id} token count: {token_count}")
