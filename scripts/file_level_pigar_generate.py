import json
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import List, Tuple

from fire import Fire
from pigar.core import RequirementsAnalyzer, _LocatableRequirements
from pigar.dist import DEFAULT_PYPI_INDEX_URL
from pigar.log import enable_pretty_logging
from pigar.log import logger as pigar_logger
from pigar.parser import DEFAULT_GLOB_EXCLUDE_PATTERNS

logger = logging.getLogger(__name__)

PigarError = Tuple[str, _LocatableRequirements]

PIGAR_UNKOWN_ERROR = "unknown"
PIGAR_UNCERTAIN_ERROR = "uncertain"

PIGAR_COMPARISON_SPECIFIER = "=="


def pigar_analyze(
    project_path: str,
    data: dict,
) -> Tuple[List[str], List[PigarError]]:
    enable_pretty_logging()

    def _dists_filter(import_name, locations, distributions, best_match):
        if best_match:
            return [best_match]
        return distributions

    file_name: str = data["file_path"].split("/")[-1]
    file_path = Path(project_path) / file_name
    file_path.write_text(data["content"])
    errors = []
    analyzer = RequirementsAnalyzer(project_path)
    analyzer.analyze_requirements(
        visit_doc_str=True,
        ignores=DEFAULT_GLOB_EXCLUDE_PATTERNS,
        dists_filter=_dists_filter,
        follow_symbolic_links=True,
        enable_requirement_annotations=False,
    )
    if analyzer.has_unknown_imports_or_uninstalled_annotations():
        analyzer.search_unknown_imports_from_index(
            dists_filter=_dists_filter,
            pypi_index_url=DEFAULT_PYPI_INDEX_URL,
            include_prereleases=True,
        )
        if analyzer.has_unknown_imports_or_uninstalled_annotations():
            import sys

            # print(Color.RED('These module(s) are still not found:'))
            analyzer.format_unknown_imports_or_uninstalled_annotations(sys.stdout)
            sys.stdout.flush()
            errors.append(PIGAR_UNKOWN_ERROR)
    if analyzer._uncertain_requirements:
        uncertain_requirements = sorted(
            analyzer._uncertain_requirements.items(), key=lambda item: item[0].lower()
        )
        pigar_logger.info(uncertain_requirements)
        errors.append(PIGAR_UNCERTAIN_ERROR)
    return dict(
        id=data["id"],
        model_name_or_path="pigar",
        pip_requirements=sorted(
            [req[1].req.name for req in analyzer._requirements.sorted_items()]
        ),
        pigar_errors=errors,
    )


def worker(cache_dir: Path, data: dict):
    with TemporaryDirectory(prefix=str(cache_dir / "tmp")) as project_path:
        return pigar_analyze(project_path, data)


def generate(
    cache_dir: str = ".cache",
    data_path: str = "data/aibuild_python_filelevel_2024-06-20.jsonl",
    output_path: str = "aibuild_python_filelevel_pigar_generated.json",
):
    cache_dir = Path(cache_dir)
    data_path = Path(data_path)
    output_path = Path(output_path)
    with data_path.open("r") as f:
        data_list = [json.loads(line) for line in f]
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count() // 2) as executor:
        results = executor.map(worker, [cache_dir] * len(data_list), data_list)
        with output_path.open("w") as f:
            json.dump(list(results), f, indent=4)


if __name__ == "__main__":
    Fire(generate)
