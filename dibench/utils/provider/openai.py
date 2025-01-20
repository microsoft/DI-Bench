import os
from typing import List

import tiktoken
from openai import AsyncAzureOpenAI, AsyncOpenAI, AzureOpenAI, OpenAI

from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    def __init__(self, model: str):
        self.model = model
        if os.getenv("OPENAI_API_KEY") is not None:
            self.client = OpenAI()
        elif os.getenv("AZURE_OPENAI_AD_TOKEN") is not None:
            self.client = AzureOpenAI()
        else:
            raise ValueError("OPENAI_API_KEY or AZURE_OPENAI_API_KEY must be set")
        self.stop_seq = []
        if self.model.startswith("gpt"):
            self.tokenizer = tiktoken.encoding_for_model(model)
        elif self.model.count("/") > 2:
            # local model path
            from transformers import AutoTokenizer

            model_name = self.model.split("/")[-3].replace("--", "/")
            if model_name.startswith("models/"):
                model_name = model_name[7:]
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, trust_remote_code=True
            )
        else:
            from transformers import AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(
                model, trust_remote_code=True
            )

    def generate_reply(
        self,
        messages: list[str],
        max_new_tokens: int = 1024,
        temperature: float = 0.0,
        n: int = 1,
    ) -> List[str]:
        assert temperature != 0 or n == 1, "n must be 1 when temperature is 0"
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_new_tokens,
            temperature=temperature,
            n=1,
        )

        return response.choices[0].message.content

    def count_tokens(self, message: str) -> int:
        return len(self.tokenizer.encode(message))


class AsyncOpenAIProvider(OpenAIProvider):
    def __init__(self, model: str):
        self.model = model
        if os.getenv("OPENAI_API_KEY") is not None:
            self.client = AsyncOpenAI()
        elif os.getenv("AZURE_OPENAI_AD_TOKEN") is not None:
            self.client = AsyncAzureOpenAI()
        else:
            raise ValueError("OPENAI_API_KEY or AZURE_OPENAI_API_KEY must be set")
        self.stop_seq = []
        if self.model.startswith("gpt"):
            self.tokenizer = tiktoken.encoding_for_model(model)
        elif self.model.count("/") > 2:
            # local model path
            from transformers import AutoTokenizer

            model_name = self.model.split("/")[-3].replace("--", "/")
            if model_name.startswith("models/"):
                model_name = model_name[7:]
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_name, trust_remote_code=True
            )
        else:
            from transformers import AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(
                model, trust_remote_code=True
            )

    async def generate_reply(
        self,
        messages: list[str],
        max_new_tokens: int = 1024,
        temperature: float = 0.0,
        n: int = 1,
    ) -> List[str]:
        assert temperature != 0 or n == 1, "n must be 1 when temperature is 0"
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_new_tokens,
            temperature=temperature,
            n=1,
        )
        return response.choices[0].message.content
