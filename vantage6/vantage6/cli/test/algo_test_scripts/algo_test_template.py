from abc import ABC, abstractmethod
from typing import TypedDict

from vantage6.client import Client


class Result(TypedDict):
    passed: bool
    result: dict


class AlgoTestTemplate(ABC):
    def __init__(
        self,
        client: Client,
    ):
        super().__init__()
        self.client = client

    @abstractmethod
    def test(
        self,
        algorithm_image: str | None = None,
        input_: dict | None = None,
        database: str | None = None,
    ) -> Result:
        pass
