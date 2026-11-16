from abc import ABC, abstractmethod

from vantage6.cli.context.node import NodeContext


class NodeDeployment(ABC):
    """Starts, stops and inspects a node on a container platform."""

    def __init__(self, ctx: NodeContext) -> None:
        self.ctx = ctx

    @property
    def name(self) -> str:
        return self.ctx.deployment_name

    @abstractmethod
    def describe_target(self) -> str:
        pass

    def prestart_checks(self) -> None:
        """Exit if the node cannot be started."""

    @abstractmethod
    def start(self, image: str) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the node and remove its algorithm runs and helpers."""

    @abstractmethod
    def is_running(self) -> bool:
        pass

    @abstractmethod
    def attach_logs(self) -> None:
        pass

    @abstractmethod
    def exec(self, command: list[str]) -> str:
        pass

    @abstractmethod
    def read_private_key(self) -> bytes | None:
        pass

    @abstractmethod
    def write_private_key(self, pem: bytes) -> None:
        pass

    @abstractmethod
    def delete_private_key(self) -> bool:
        pass
