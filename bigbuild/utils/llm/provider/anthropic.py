import os
from typing import List

from anthropic import Client

from bigbuild.utils.llm.provider.base import BaseProvider
from bigbuild.utils.llm.provider.request.anthropic import make_auto_request


class AnthropicProvider(BaseProvider):
    def __init__(self, model):
        self.model = model
        self.client = Client(api_key=os.getenv("ANTHROPIC_KEY"))

    def generate_reply(
        self, message, n=1, max_tokens=1024, temperature=0.0, system_msg=None
    ) -> List[str]:
        assert temperature != 0 or n == 1, "n must be 1 when temperature is 0"
        replies = []
        for _ in range(n):
            reply = make_auto_request(
                self.client,
                message=message,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                system_msg=system_msg,
            )
            replies.append(reply.content[0].text)

        return replies

    def count_tokens(self, message: str) -> int:
        return len(self.client.count_tokens(message))
