from abc import ABC, abstractmethod
from typing import List


class BaseProvider(ABC):
    @abstractmethod
    def generate_reply(
        self,
        message: str,
        n: int = 1,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        system_msg: str = None,
    ) -> List[str]:
        ...

    @abstractmethod
    def count_tokens(self, message: str) -> int:
        ...
