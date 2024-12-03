from typing import TypeAlias

from .azure import AzureOpenaiProvider
from .openai import OpenAIProvider

LLMProvider: TypeAlias = AzureOpenaiProvider | OpenAIProvider


def make_provider(
    model: str,
    backend: str,
    base_url: str | None = None,
    tensor_parallel_size: int = 1,
    code_context_size: int = 1024 * 100,
    trust_remote_code: bool = False,
    attn_implementation=None,
):
    if backend == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(model, base_url=base_url)
    elif backend == "azure":
        from .azure import AzureOpenaiProvider

        return AzureOpenaiProvider(model)
    elif backend == "vllm":
        from .vllm import VllmProvider

        return VllmProvider(
            model,
            tensor_parallel_size=tensor_parallel_size,
            max_model_len=int(code_context_size * 1.2),  # Magic number
            trust_remote_code=trust_remote_code,
        )
    elif backend == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(model)
    elif backend == "hf":
        from .hf import HfProvider

        return HfProvider(
            model,
            trust_remote_code=trust_remote_code,
            attn_implementation=attn_implementation,
        )
    elif backend == "google":
        from .google import GoogleProvider

        return GoogleProvider(model)
    else:
        raise ValueError(f"Unknown backend: {backend}")
