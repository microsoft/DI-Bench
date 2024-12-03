from pathlib import Path

from .base import Builder, Repo

__all__ = [
    "make_builder",
    "Builder",
    "Repo",
]


def make_builder(
    builder_type: str,
    repo: Repo,
    build_cache: Path,
    model_name: str = "gpt-4o-20240806",
    backend: str = "azure",
    resume: bool = True,
    max_code_context: int = 1024 * 100,
    max_new_tokens: int = 1024 * 8,
    check_context: bool = False,
    base_url: str | None = None,
    tensor_parallel_size: int = 1,
    trust_remote_code: bool = False,
    attn_implementation=None,
):
    assert build_cache.exists(), f"cache dir {build_cache} for builder not exists"
    if builder_type == "slide":
        from .slide.builder import SlideBuilder

        return SlideBuilder(
            repo=repo,
            model_name=model_name,
            backend=backend,
            cache_dir=build_cache,
            resume=resume,
            max_seq_len=max_code_context,
            max_new_tokens=max_new_tokens,
            base_url=base_url,
            tensor_parallel_size=tensor_parallel_size,
            trust_remote_code=trust_remote_code,
            attn_implementation=attn_implementation,
            check_context=check_context,
        )
    elif builder_type == "pattern":
        from .pattern.builder import PatternBuilder

        return PatternBuilder(
            repo=repo,
            model_name=model_name,
            backend=backend,
            cache_dir=build_cache,
            resume=resume,
            max_seq_len=max_code_context,
            max_new_tokens=max_new_tokens,
            base_url=base_url,
            tensor_parallel_size=tensor_parallel_size,
            trust_remote_code=trust_remote_code,
            attn_implementation=attn_implementation,
        )
    else:
        raise ValueError(f"Unknown builder type {builder_type}")
