"""In-memory stand-in for the parts of the Docker SDK the Docker runtime uses."""

import io
import tarfile
from collections.abc import Callable

from docker.errors import APIError, ImageNotFound, NotFound


def _matches(labels: dict, filters: dict | None) -> bool:
    for label in (filters or {}).get("label", []):
        key, _, value = label.partition("=")
        if labels.get(key) != value:
            return False
    return True


class FakeContainer:
    def __init__(self, client: "FakeDockerClient", image: str, name: str, **kwargs):
        self.client = client
        self.image = image
        self.name = name
        self.labels = kwargs.pop("labels", None) or {}
        self.command = kwargs.pop("command", None)
        self.environment = kwargs.pop("environment", None) or {}
        self.mounts = kwargs.pop("mounts", None) or []
        self.network_mode = kwargs.pop("network_mode", None)
        network = kwargs.pop("network", None)
        self.options = kwargs
        self.archives: dict[str, bytes] = {}
        self.output = b""
        self.removed = False
        self.attrs = {
            "State": {"Status": "created", "ExitCode": 0, "OOMKilled": False},
            "NetworkSettings": {"Networks": {}},
        }
        if network:
            client.networks.get(network).connect(self)

    @property
    def status(self) -> str:
        return self.attrs["State"]["Status"]

    def start(self) -> None:
        self.attrs["State"]["Status"] = "running"
        if self.client.on_start:
            self.client.on_start(self)

    def finish(self, exit_code: int = 0, output: bytes = b"", oom: bool = False):
        self.attrs["State"].update(Status="exited", ExitCode=exit_code, OOMKilled=oom)
        self.output += output

    def wait(self, timeout=None) -> dict:
        if self.status != "exited":
            raise TimeoutError("still running")
        return {"StatusCode": self.attrs["State"]["ExitCode"]}

    def logs(self, stdout=True, stderr=True, stream=False, follow=False):
        if stream:
            return iter([self.output])
        return self.output

    def put_archive(self, path: str, data: bytes) -> bool:
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            for member in archive.getmembers():
                content = archive.extractfile(member).read()
                self.archives[f"{path}/{member.name}"] = content
        return True

    def remove(self, force: bool = False) -> None:
        if self.removed:
            raise NotFound("gone")
        if self.status == "running" and not force:
            raise APIError("running")
        self.removed = True
        self.client.containers.items.pop(self.name, None)
        for network in self.client.networks.items.values():
            network.members.pop(self.name, None)


class FakeContainers:
    def __init__(self, client: "FakeDockerClient"):
        self.client = client
        self.items: dict[str, FakeContainer] = {}

    def create(self, image: str, name: str | None = None, **kwargs) -> FakeContainer:
        if image not in self.client.images.items:
            raise ImageNotFound(image)
        if name in self.items:
            raise APIError(f"Conflict: {name}")
        container = FakeContainer(self.client, image, name, **kwargs)
        self.items[name] = container
        return container

    def get(self, name: str) -> FakeContainer:
        if name not in self.items:
            raise NotFound(name)
        return self.items[name]

    def list(self, all: bool = False, filters: dict | None = None):
        status = (filters or {}).get("status")
        return [
            c
            for c in self.items.values()
            if _matches(c.labels, filters)
            and (all or c.status == "running")
            and (status is None or c.status == status)
        ]


class FakeImages:
    def __init__(self):
        self.items: set[str] = set()
        self.pulls: list[tuple[str, str | None, dict | None]] = []
        self.missing_in_registry: set[str] = set()

    def get(self, image: str):
        if image not in self.items:
            raise ImageNotFound(image)
        return image

    def pull(self, repository: str, tag: str | None = None, auth_config=None):
        image = f"{repository}:{tag}" if tag else repository
        self.pulls.append((repository, tag, auth_config))
        if image in self.missing_in_registry:
            raise NotFound(f"manifest for {image} not found")
        self.items.add(image)
        return image


class FakeNetwork:
    def __init__(self, client: "FakeDockerClient", name: str, internal: bool, labels):
        self.client = client
        self.name = name
        self.attrs = {"Internal": internal, "Labels": labels or {}}
        self.members: dict[str, tuple[FakeContainer, list[str]]] = {}

    @property
    def containers(self) -> list[FakeContainer]:
        return [c for c, _ in self.members.values()]

    def connect(self, container, aliases: list[str] | None = None) -> None:
        if isinstance(container, str):
            container = self.client.containers.get(container)
        self.members[container.name] = (container, aliases or [])
        container.attrs["NetworkSettings"]["Networks"][self.name] = {}

    def disconnect(self, container, force: bool = False) -> None:
        self.members.pop(container.name, None)
        container.attrs["NetworkSettings"]["Networks"].pop(self.name, None)

    def reload(self) -> None:
        pass

    def remove(self) -> None:
        if self.members:
            raise APIError("network has active endpoints")
        self.client.networks.items.pop(self.name)


class FakeNetworks:
    def __init__(self, client: "FakeDockerClient"):
        self.client = client
        self.items: dict[str, FakeNetwork] = {}

    def create(self, name, driver="bridge", internal=False, labels=None):
        network = FakeNetwork(self.client, name, internal, labels)
        self.items[name] = network
        return network

    def get(self, name: str) -> FakeNetwork:
        if name not in self.items:
            raise NotFound(name)
        return self.items[name]

    def list(self, names: list[str] | None = None) -> list[FakeNetwork]:
        return [n for n in self.items.values() if not names or n.name in names]


class FakeDockerClient:
    def __init__(self):
        self.images = FakeImages()
        self.containers = FakeContainers(self)
        self.networks = FakeNetworks(self)
        # Called when a container starts, e.g. to make it finish
        self.on_start: Callable[[FakeContainer], None] | None = None

    def ping(self) -> bool:
        return True

    def add_node_container(self, name: str) -> FakeContainer:
        self.images.items.add("node-image")
        return self.containers.create("node-image", name=name)
