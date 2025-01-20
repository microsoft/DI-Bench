from abc import ABC, abstractmethod
from typing import List


class BaseProvider(ABC):
    @abstractmethod
    def generate_reply(
        self,
        messages: list[str],
        max_new_tokens: int = 1024,
        temperature: float = 0.0,
        n: int = 1,
    ) -> List[str]:
        ...

    @abstractmethod
    def count_tokens(self, message: str) -> int:
        ...


# https://github.com/evalplus/repoqa/blob/main/repoqa/provider/request/__init__.py
def hacky_assistant_stop_seq(tokenizer) -> str:
    _magic_string_ = "&== [HACKY SPLITTER] ==&"
    return tokenizer.apply_chat_template(
        [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": _magic_string_},
        ],
        tokenize=False,
    ).split(_magic_string_)[-1]
