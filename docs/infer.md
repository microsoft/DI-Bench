## 🧐 Dependency Inference

we support many llm backends.

### OpenAI
```bash 
export OPENAI_API_KEY=<your-api-key>
# <path-to-repo-instances-dir> is the directory where the your repo instances are downloaded and unzipped.
dibench.depinfer --model "gpt-4o-2024-0806" \
                 --method ["all-in-one" | "import-only" | "file-iter"] \
                 --repo_instances_dir <path-to-repo-instances-dir>
```

### AZURE
```bash
export AZURE_OPENAI_AD_TOKEN=<your-ad-token>
export AZURE_OPENAI_ENDPOINT=<your-endpoint>
export OPENAI_API_VERSION=<your-api-version>
dibench.depinfer --model <deplyment-id> \
                 --method ["all-in-one" | "import-only" | "file-iter"] \
                 --repo_instances_dir <path-to-repo-instances-dir>
```

### `openai` compatible servers(e.g. [vllm](https://github.com/vllm-project/vllm), [sglang](https://github.com/sgl-project/sglang)) 
```bash
# DeepSeek
export OPENAI_API_KEY=<your-api-key> # https://platform.deepseek.com/api_keys
export OPENAI_BASE_URL=https://api.deepseek.com
dibench.depinfer --model "deepseek-chat" \
                 --method ["all-in-one" | "import-only" | "file-iter"] \
                 --repo_instances_dir <path-to-repo-instances-dir>

# Grok
export OPENAI_API_KEY=<your-api-key> # https://console.x.ai/
export OPENAI_BASE_URL=https://api.x.ai/v1
dibench.depinfer --model "grok-beta" \
                 --method ["all-in-one" | "import-only" | "file-iter"] \
                 --repo_instances_dir <path-to-repo-instances-dir>

# vLLM/sgLang servers
export OPENAI_API_KEY=<your-api-key> 
# launch vllm service: https://docs.vllm.ai/en/latest/serving/deploying_with_docker.html
# launch sglang service: https://docs.sglang.ai/backend/openai_api_completions.html
export OPENAI_BASE_URL=<your-base-url>
dibench.depinfer --model "deepseek-ai/DeepSeek-V3" \
                 --method ["all-in-one" | "import-only" | "file-iter"] \
                 --repo_instances_dir <path-to-repo-instances-dir>
```