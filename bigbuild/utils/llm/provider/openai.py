import os
from typing import List

import tiktoken
from openai import Client

from bigbuild.utils.llm.provider.base import BaseProvider
from bigbuild.utils.llm.provider.request.openai import make_auto_request


class OpenAIProvider(BaseProvider):
    def __init__(self, model: str, base_url: str = None):
        self.model = model
        self.client = Client(
            api_key=os.getenv("OPENAI_API_KEY", "none"), base_url=base_url
        )
        self.stop_seq = []
        if self.model.startswith("gpt"):
            self.tokenizer = tiktoken.encoding_for_model(model)
        else:
            from transformers import AutoTokenizer

            self.tokenizer = AutoTokenizer.from_pretrained(
                model, trust_remote_code=True
            )

    def generate_reply(
        self, message, n=1, max_tokens=1024, temperature=0.0, system_msg=None
    ) -> List[str]:
        assert temperature != 0 or n == 1, "n must be 1 when temperature is 0"
        replies = make_auto_request(
            self.client,
            message=message,
            model=self.model,
            temperature=temperature,
            n=n,
            max_tokens=max_tokens,
            system_msg=system_msg,
            stop=self.stop_seq,
        )

        return [reply.message.content for reply in replies.choices]

    def count_tokens(self, message: str) -> int:
        return len(self.tokenizer.encode(message))
