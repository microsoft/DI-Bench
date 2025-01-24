## 🐳 Dataset Curation
_How our dataset was curated? How to create the benchmark instances?_

To obtain testable real-world repositories from GitHub, we propose a fully automated curation pipeline that utilizes GitHub Actions CI and LLM assistance, eliminating the need for human involvement in benchmark construction.

### Github crawling
```shell
python -m dibench.curate.crawling --help
```
1) Searches GitHub for repositories in `star_range` for `language` (10-star batches).

2) Check each repo for workflows, if found, dump repo instance into JSONL.

### Test CI locating

```shell
python -m dibench.curate.curate --help
```
1) Locate the test CI file
2) Locate the test job in the CI file
3) Get the ACT command
4) Sanitize & Mask
5) Get the gold patch

### Execution verifying

```shell
python -m dibench.curate.verify --help
```

Expected:
1) Tests Pass when dependencies unmasked
2) Tests Fail when dependencies masked
