import json
import os
from typing import List

import tiktoken
from openai import AzureOpenAI

from bigbuild.utils.llm.provider.base import BaseProvider
from bigbuild.utils.llm.provider.request.azure import make_auto_request


class AzureOpenaiProvider(BaseProvider):
    def __init__(self, model):
        self.model = model

        self.azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
        self.api_version = os.environ.get("OPENAI_API_VERSION", "2024-06-01")

        key = os.environ.get("OPENAI_API_KEY")
        self.client = AzureOpenAI(
            api_version=self.api_version,
            azure_endpoint=self.azure_endpoint,
            api_key=key,
        )

        self.stop_seq = []
        self.encoding = tiktoken.encoding_for_model(model)

    def generate_reply(
        self, message, n=1, max_tokens=1024, temperature=0.0, system_msg=None
    ) -> List[str]:
        assert temperature != 0 or n == 1, "n must be 1 when temperature is 0"
        replies = make_auto_request(
            client=self.client,
            message=message,
            model=self.model,
            temperature=temperature,
            n=n,
            max_tokens=max_tokens,
            system_msg=system_msg,
            stop=self.stop_seq,
        )
        return [reply.message.content for reply in replies.choices]

    def generate_json(
        self, message, n=1, max_tokens=1024, temperature=0.0, system_msg=None
    ) -> List[dict]:
        assert temperature != 0 or n == 1, "n must be 1 when temperature is 0"
        replies = make_auto_request(
            client=self.client,
            message=message,
            model=self.model,
            temperature=temperature,
            n=n,
            max_tokens=max_tokens,
            system_msg=system_msg,
            stop=self.stop_seq,
            response_format={"type": "json_object"},
        )

        return [json.loads(reply.message.content) for reply in replies.choices]

    def count_tokens(self, message: str) -> int:
        tokens = self.encoding.encode(message, disallowed_special=())
        return len(tokens)
