import docker
import json
import os
import shutil
import base64
import hashlib
import time

from pathlib import Path

from vantage6.common.globals import APPNAME
from vantage6.common import debug, info, error
from vantage6.common.docker.addons import get_container
from vantage6.common.docker.network_manager import NetworkManager
from vantage6.common import split_rabbitmq_uri
from vantage6.cli.context.server import ServerContext
from vantage6.cli.rabbitmq.definitions import RABBITMQ_DEFINITIONS
from vantage6.cli.globals import RABBIT_TIMEOUT

DEFAULT_RABBIT_IMAGE = "harbor2.vantage6.ai/infrastructure/rabbitmq"
RABBIT_CONFIG = "rabbitmq.config"
RABBIT_DIR = "rabbitmq"


class RabbitMQManager:
    """
    Manages the RabbitMQ docker container

    Parameters
    ----------
    ctx: ServerContext
        Configuration object
    network_mgr: NetworkManager
        Network manager for network in which server container resides
    image: str
        Docker image to use for RabbitMQ container. By default, the image
        harbor2.vantage6.ai/infrastructure/rabbitmq is used.
    """

    def __init__(
        self, ctx: ServerContext, network_mgr: NetworkManager, image: str = None
    ) -> None:
        self.ctx = ctx
        self.queue_uri = self.ctx.config["rabbitmq"].get("uri")
        rabbit_splitted = split_rabbitmq_uri(self.queue_uri)
        self.rabbit_user = rabbit_splitted["user"]
        self.rabbit_pass = rabbit_splitted["password"]
        self.vhost = rabbit_splitted["vhost"]
        self.port = rabbit_splitted["port"]
        self.host = rabbit_splitted["host"]
        self.definitions_file = Path(self.ctx.data_dir / "definitions.json")
        self.network_mgr = network_mgr

        self.docker = docker.from_env()
        self.image = image if image else DEFAULT_RABBIT_IMAGE

    def start(self) -> None:
        """
        Start a docker container which runs a RabbitMQ queue
        """
        # get volumes which contain rabbitMQ configuration and a location to
        # save rabbitMQ files so that they persist after container is stopped
        volumes = self._get_volumes()

        # expose port 5672 inside the container as port 5672 on the host, and
        # same for 15672 in container to 8080 on host
        # TODO check if these ports are not already used on the host
        ports = {
            f"{self.port}/tcp": self.port,
            # TODO this is for the management tool, do we keep this? Not used
            # at the moment..
            "15672/tcp": 8080,
        }

        # check if a RabbitMQ container is already running
        self.rabbit_container = get_container(docker_client=self.docker, name=self.host)
        if self.rabbit_container:
            info("RabbitMQ is already running! Linking the server to that " "queue")
            if not self.network_mgr.contains(self.rabbit_container):
                self.network_mgr.connect(self.rabbit_container)
            return

        # start rabbitMQ container
        self.rabbit_container = self.docker.containers.run(
            name=self.host,
            image=self.image,
            volumes=volumes,
            ports=ports,
            detach=True,
            restart_policy={"Name": "unless-stopped"},
            hostname=self.host,
            labels={
                f"{APPNAME}-type": "rabbitmq",
            },
            network=self.network_mgr.network_name,
        )

        # Wait until RabbitMQ is up before continuing with other stuff
        self._wait_for_startup()

    def _wait_for_startup(self) -> None:
        """Wait until RabbitMQ has been initialized"""
        interval = 10
        attempts = int((RABBIT_TIMEOUT + interval) / interval)
        is_running = False
        for _ in range(attempts):
            if self.is_running():
                is_running = True
                break
            debug(f"RabbitMQ is not yet running. Retrying in {interval}s...")
            time.sleep(interval)
        if is_running:
            info("RabbitMQ was started successfully!")
        else:
            error("Could not start RabbitMQ! Exiting...")
            exit(1)

    def is_running(self) -> bool:
        """
        Returns
        -------
        bool
            Whether the container has fully initialized RabbitMQ or not
        """
        response = self.rabbit_container.exec_run(
            cmd="rabbitmqctl status --formatter json"
        )
        return response.exit_code == 0

    def _get_volumes(self) -> dict:
        """
        Prepare the volumes for the RabbitMQ container. The RabbitMQ should
        set up the right vhost and users to allow the server to communicate
        with RabbitMQ as configured.

        Returns
        -------
        dict
            Dictionary with the volumes to mount in the RabbitMQ container
        """
        # default RabbitMQ configuration: replace the user/password with the
        # credentials from the configuraiton
        rabbit_definitions = self._get_rabbitmq_definitions()

        # write the RabbitMQ definition to file(s)
        with open(self.definitions_file, "w") as f:
            json.dump(rabbit_definitions, f, indent=2)

        # write RabbitMQ config to file
        rabbit_conf = Path(__file__).parent.resolve() / RABBIT_CONFIG
        shutil.copyfile(rabbit_conf, self.ctx.data_dir / RABBIT_CONFIG)

        # check if a directory for persistent RabbitMQ storage exists,
        # otherwise create it
        rabbit_data_dir = self.ctx.data_dir / RABBIT_DIR
        if not rabbit_data_dir.exists():
            rabbit_data_dir.mkdir(parents=True, exist_ok=True)

        return {
            self.definitions_file: {
                "bind": "/etc/rabbitmq/definitions.json",
                "mode": "ro",
            },
            self.ctx.data_dir
            / RABBIT_CONFIG: {"bind": "/etc/rabbitmq/rabbitmq.config", "mode": "ro"},
            rabbit_data_dir: {"bind": "/var/lib/rabbitmq", "mode": "rw"},
        }

    def _get_rabbitmq_definitions(self) -> dict:
        """
        Get startup definitions (users/vhosts etc) for RabbitMQ container

        Returns
        -------
        Dict:
            dictionary with all users/vhosts etc that must be generated on
            startup of RabbitMQ
        """
        rabbit_definitions = RABBITMQ_DEFINITIONS
        rabbit_definitions["users"][0]["name"] = self.rabbit_user
        rabbit_definitions["permissions"][0]["user"] = self.rabbit_user
        rabbit_definitions["users"][0]["password_hash"] = self._get_hashed_pw(
            self.rabbit_pass
        )
        rabbit_definitions["vhosts"][0]["name"] = self.vhost
        rabbit_definitions["permissions"][0]["vhost"] = self.vhost
        return rabbit_definitions

    def _get_hashed_pw(self, pw: str) -> str:
        """
        Hash a user-defined password for RabbitMQ

        Parameters
        ----------
        pw: str
            The password for RabbitMQ

        Returns
        -------
        str
            Hashed password for RabbitMQ
        """

        # Generate a random 32 bit salt:
        salt = os.urandom(4)

        # Concatenate that with the UTF-8 representation of the password
        tmp0 = salt + pw.encode("utf-8")

        # Take the SHA256 hash and get the bytes back
        tmp1 = hashlib.sha256(tmp0).digest()

        # Concatenate the salt again:
        salted_hash = salt + tmp1

        # convert to base64 encoding:
        pass_hash = base64.b64encode(salted_hash)
        return pass_hash.decode("utf-8")
