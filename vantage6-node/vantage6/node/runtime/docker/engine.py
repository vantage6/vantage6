from dataclasses import dataclass

from docker.types import Mount


@dataclass(frozen=True)
class EngineSettings:
    """What differs between container engines that offer the Docker API."""

    name: str
    # Where the node finds the engine API inside the node container
    base_url: str
    # Name under which containers reach the container host
    host_gateway_name: str

    def bind(self, source: str, target: str, read_only: bool) -> Mount:
        return Mount(target=target, source=source, type="bind", read_only=read_only)


DOCKER = EngineSettings(
    name="docker",
    base_url="unix:///var/run/docker.sock",
    host_gateway_name="host.docker.internal",
)
