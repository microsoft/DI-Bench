# `🛠️ BigBuildBench`

<p align="center">
<a href="https://huggingface.co/datasets/BigBuildBench/BigBuildBench"><img src="https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-BigBuildBench-%23ff8811.svg"></a>
<a href="https://github.com/pre-commit/pre-commit"><img src="https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit" alt="pre-commit" style="max-width:100%;"></a>
<a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json"></a>
</p>

🔎 Evaluating Large Language Models on Dependency Inference

## 🚀 Quick Start

Ensure that Docker engine is installed and running on your machine.

> [!Important]
>
>
> Our testing infrastructure requires [⚙️sysbox](https://github.com/nestybox/sysbox) (a Docker runtime) to be installed on your system to ensure isolation and security.

```shell
# Suggested Python version: 3.12
pip install .
```

## ⬇️ Downloads

| Datasets |
| - |
| [🤗 BigBuildBench](https://huggingface.co/datasets/BigBuildBench/BigBuildBench) |

```shell
python scripts/precache_repos
```

## 😎 Evaluation

```shell
python -m bigbuild.harness.run_evaluator --help
```


## Run Experiments with VLLM

### start server
```shell
# nohup ./start_server [model_name] [port] &
nohup ./start_server deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct 8000 &
```
### run experiments
```shell
# nohup ./inference [model_name] [cache_dir] [port] &
./inference deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct .cache 8000 &
```

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
