#! /bin/bash
set -ex


model=$1
cache=$2
port=$3
max_seq_len=131072
max_output_len=8192

base_url="http://localhost:$port/v1"

TOKENIZERS_PARALLELISM=true python -m bigbuild.inference.run_builder --run_id final \
     --builder_type slide \
     --language python \
     --dataset_name_or_path "BigBuildBench/BigBuildBench-Mini" \
     --repo_cache $cache/repo-mini \
     --build_cache $cache/build-mini \
     --model_name  $model \
     --backend openai \
     --base_url $base_url \
     --max_code_context $max_seq_len  \
     --max_new_tokens $max_output_len \

TOKENIZERS_PARALLELISM=true python -m bigbuild.inference.run_builder --run_id final \
     --builder_type slide \
     --language rust \
     --dataset_name_or_path "BigBuildBench/BigBuildBench-Mini" \
     --repo_cache $cache/repo-mini \
     --build_cache $cache/build-mini \
     --model_name  $model \
     --backend openai \
     --base_url $base_url \
     --max_code_context $max_seq_len  \
     --max_new_tokens $max_output_len \

TOKENIZERS_PARALLELISM=true python -m bigbuild.inference.run_builder --run_id final \
     --builder_type slide \
     --language csharp \
     --dataset_name_or_path "BigBuildBench/BigBuildBench-Mini" \
     --repo_cache $cache/repo-mini \
     --build_cache $cache/build-mini \
     --model_name  $model \
     --backend openai \
     --base_url $base_url \
     --max_code_context $max_seq_len  \
     --max_new_tokens $max_output_len \

TOKENIZERS_PARALLELISM=true python -m bigbuild.inference.run_builder --run_id final \
     --builder_type slide \
     --language rust \
     --dataset_name_or_path "BigBuildBench/BigBuildBench-Mini" \
     --repo_cache $cache/repo-mini \
     --build_cache $cache/build-mini \
     --model_name  $model \
     --backend openai \
     --base_url $base_url \
     --max_code_context $max_seq_len  \
     --max_new_tokens $max_output_len \
