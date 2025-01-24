# `🛠️ DI-Bench`: Benchmarking Large Language Models on Dependency Inference with Testable Repositories

## 🚀 Quick Start

Ensure that Docker engine is installed and running on your machine.

> [!Important]
>
>
> Our testing infrastructure requires [⚙️sysbox](https://github.com/nestybox/sysbox) (a Docker runtime) to be installed on your system to ensure isolation and security.

```shell
# Suggested Python version: 3.10
pip install ".[eval,llm,pattern]"

# Used for authentication in the local CI runner to enable downloading actions from GitHub, requiring 0 permission
export GITHUB_TOKEN=<your_github_token>
```

## ⬇️ Download DI-Bench Dataset

[Dataset release page](https://github.com/microsoft/DI-Bench/releases)

After downloading the dataset, extract the `*.tar.gz` into the data directory: `.cache/repo-data/{language}`. Replace `{language}` with `python`, `rust`, `csharp`, or `javascript`.

```bash
mkdir -p .cache/repo-data
tar -xvzf .cache/dibench-regular-python.tar.gz -C .cache/repo-data
# ...
```

Each repository instance's data can be found in `.cache/repo-data/{language}/{instance_id}`.

## 😎 Evaluation

Evaluate the correctness of inferred dependencies by checking if the project's tests pass.

```shell
dibench.eval \
    --result_dir [results_dir] \ # the root of generated results, e.g. tests/data/example-results
    --repo_instances_dir [repo_instances_dir] \ # extracted repo data path
    --dataset_name_or_path [regular_dataset_path/large_dataset_path] # *.jsonl
```

## 📃 Documentations
- [Dataset Curation](./docs/curate.md)
- [Infer Dependencies Using LLMs](./docs/infer.md)
