#! /bin/bash

results_dir=$1
id_range=${2:-"0-400"}
concurrency=${3:-10}
resume=${4:-False}
repo_cache=${5:-".cache/repo-mini"}

task_start=$(echo $id_range | cut -d "-" -f 1)
task_end=$(echo $id_range | cut -d "-" -f 2)
echo "results_dir: $results_dir"
echo "id_range: $task_start-$task_end"
echo "concurrency: $concurrency"
echo "resume: $resume"
echo "repo_cache: $repo_cache"

function run() {
    python -m dibench.eval \
        --result_dir $results_dir \
        --repo_cache $repo_cache \
        --id_range ${start},${end} \
        --exec_eval False \
        --resume $resume
}


task_num=$(((${task_end}-${task_start})/${concurrency}))
for i in $(seq 0 $((${concurrency}-1)))
do
    start=$((${i}*${task_num}+${task_start}))
    end=$((${start}+${task_num}))
    echo "evaluating ${start}-${end}"
    run ${start} ${end} &
done
wait
