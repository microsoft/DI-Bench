from typing import Literal

from .base import BaseProvider

__all__ = ["get_llm", "BaseProvider"]


def get_llm(
    model: str,
    model_backend: Literal["openai"] = "openai",
    use_async: bool = False,
):
    if model_backend == "openai":
        from .openai import AsyncOpenAIProvider, OpenAIProvider

        return OpenAIProvider(model) if not use_async else AsyncOpenAIProvider(model)
    else:
        raise ValueError(f"Not supported backend: {model_backend}")
