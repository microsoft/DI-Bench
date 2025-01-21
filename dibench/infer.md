## 🤔 Infer Dependencies Using LLMs

### Configure LLM API Key

Firstly, set environment variables for LLM providers.
```shell
# for OpenAI
export OPENAI_API_KEY=<your_openai_apikey>
# for Azure
export AZURE_OPENAI_AD_TOKEN=<your_azure_token>
```

### Run All-In-One prompt strategy

**Prepare prompts**
```shell
python -m dibench.make_prompts \
     --result_path results/bigbuild-prompts.jsonl \
     --dataset [dataset_path]
```

**Generate**
```shell
python -m dibench.buildgen \
    --prompt_path [prompt_path] \ # generated in 'prepare prompts'
    --target_dir [result_dir] \ # results will be saved in result_dir\\model
    --model_name [model] \
    --backend "openai" \
    # --base_url [base_url] \ # if you using vllm service
    --id_range ${start},${end}
```

### Run Imports-Only
**prepare prompts**
```shell
poetry run python -m bigbuild.make_prompts \
     --result_path results/bigbuild-prompts.jsonl \
     --dataset [dataset_path] \
     --pattern \
```

**Generate**
```shell
python -m bigbuild.buildgen \
    --prompt_path [prompt_path] \ # generated in 'prepare prompts'
    --target_dir [result_dir] \ # results will be saved in result_dir\model
    --model_name [model] \
    --backend "openai" \
    # --base_url [base_url] \ # if you using vllm service
```

### Run File-Iterate
```shell
python -m bigbuild.inference.run_builder \
    --model [model] \
    --backend  "openai" \
    # --base_url [base_url] # if you using vllm server
    --dataset_name_or_path [dataset_path] \
    --repo_cache [repo_path] \
```
Note: the dataset and repo_cache should align, both regular and large
