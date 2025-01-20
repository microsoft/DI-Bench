#! /bin/bash
set -ex


model=$1
port=$2
max_seq_len=12000
max_output_len=8000

# NCCL_IGNORE_DISABLED_P2P=1  vllm serve $model --port $port --trust-remote-code  --gpu-memory-utilization 0.99 --tensor-parallel-size 2
NCCL_IGNORE_DISABLED_P2P=1  vllm serve $model --port $port --trust-remote-code  --gpu-memory-utilization 0.99
