"""
This module contains the SSH tunnel class. It is responsible for creating
an SSH configuration file and starting an SSH tunnel container.

The SSH tunnel container is used to create a secure connection between the
private network of the node and an external data source. This can then be used
by the algorithm containers to access the data source. Multiple SSH tunnels
can be created, each with a different configuration.
"""

import logging
import os

from typing import NamedTuple
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from vantage6.common import logger_name
from vantage6.common.globals import APPNAME
from vantage6.common.docker.addons import (
    remove_container,
    running_in_docker,
    remove_container_if_exists,
)
from vantage6.node.docker.docker_base import DockerBaseManager
from vantage6.node.docker.docker_manager import NetworkManager
from vantage6.node.globals import SSH_TUNNEL_IMAGE, PACKAGE_FOLDER
from vantage6.node._version import major_minor

log = logging.getLogger(logger_name(__name__))


class SSHTunnelConfig(NamedTuple):
    """
    Data class to store the configuration of the SSH tunnel.

    Attributes
    ----------
    username : str
        Username of the remote server
    hostname : str
        Hostname of the remote server
    port : int
        SSH port of the remote server
    identity_file : str
        Identity file of the user to connect to the remote server
    local_ip : str
        IP of the app you want to tunnel on the remote machine
    local_port : int
        Port of the app you want to tunnel on the remote machine
    bind_ip : str
        IP where you want to bind the remote app to in the tunnel container
    bind_port : int
        Port where you want to bind the remote app to in the tunnel container
    """

    username: str
    hostname: str
    port: int
    identity_file: str
    local_ip: str
    local_port: int
    bind_ip: str
    bind_port: int


class KnownHostsConfig(NamedTuple):
    """
    Data class to store the configuration of the known_hosts file.

    Attributes
    ----------
    hostname : str
        Hostname of the remote server
    fingerprint : str
        Fingerprint of the remote server
    """

    hostname: str
    fingerprint: str


class SSHTunnel(DockerBaseManager):
    def __init__(
        self,
        isolated_network_mgr: NetworkManager,
        config: dict,
        node_name: str,
        config_volume: str,
        tunnel_image: str | None = None,
    ) -> None:
        """
        Create a tunnel from the isolated network to a remote machine and
        bind the remote port to a local ssh-tunnel container to be used by
        an algorithm.

        Parameters
        ----------
        isolated_network_mgr : NetworkManager
            Isolated network manager
        config : dict
            ssh tunnel configuration
        node_name : str
            Node name to derive the ssh tunnel container name
        config_volume : str
            Name of the ssh config volume (or local path)
        tunnel_image : str | None, optional
            User defined image to use for the tunnel, by default None

        Raises
        ------
        KeyError
            Missing key in the configuration
        """

        super().__init__(isolated_network_mgr)

        # reference to the SSH tunnel container
        self.container = None

        self.container_name = f"{APPNAME}-{node_name}-ssh-tunnel"

        # Place where we can store the SSH configuration file and the
        # known_hosts file.
        self.config_volume = config_volume

        self.config_folder = (
            Path("/mnt/ssh") if running_in_docker() else Path(self.config_volume)
        )

        try:
            # hostname of the tunnel which can be used by the algorithm
            # containers
            self.hostname = config["hostname"]
            log.debug(f"SSH tunnel hostname: {self.hostname}")

            # Create the SSH configuration, which can later be mounted by the
            # SSH tunnel container
            self.ssh_tunnel_config, self.known_hosts_config = self.read_config(config)
        except KeyError as e:
            # parent class should handle this
            raise KeyError(f"Invalid SSH tunnel configuration: {e}")

        # The image is overridable by the user configuration
        self.image = (
            tunnel_image if tunnel_image else f"{SSH_TUNNEL_IMAGE}:{major_minor}"
        )
        log.debug(f"SSH tunnel image: {self.image}")

        # Create the SSH configuration files
        self.create_ssh_config_file(self.ssh_tunnel_config)
        self.create_known_hosts_file(self.known_hosts_config)

        self.start()
        log.info(f"SSH tunnel {self.hostname} started")

    @staticmethod
    def read_config(config: dict) -> tuple[SSHTunnelConfig, KnownHostsConfig]:
        """
        Read the SSH configuration from the config

        Parameters
        ----------
        config: dict
            Dictionary containing the SSH configuration

        Returns
        -------
        SSHTunnelConfig, KnownHostsConfig
            SSH configuration files for the SSH tunnel container

        Notes
        -----
        The SSH configuration is stored in the following format:

        ```yaml
        ssh-tunnels:
          - hostname: "my-ssh-host"
            ssh:
              host: "my-ssh-host"
              port: 22
              fingerprint: "my-ssh-host-fingerprint"
              identity:
                username: "my-ssh-username"
                key: "/path/to/my/ssh/key"
            tunnel:
              bind:
                ip: x.x.x.x
                port: 1234
              dest:
                ip: 127.0.0.1
                port: 5678
        ```
        """
        log.debug("Reading SSH tunnel configuration")
        bind = config["tunnel"]["bind"]
        dest = config["tunnel"]["dest"]
        ssh = config["ssh"]
        identity = ssh["identity"]

        # SSH config to connect to the remote server
        ssh_tunnel_config = SSHTunnelConfig(
            username=identity["username"],
            hostname=ssh["host"],
            port=ssh["port"],
            identity_file=f"/root/.ssh/{config['hostname']}.pem",
            bind_ip=bind["ip"],
            bind_port=bind["port"],
            local_ip=dest["ip"],
            local_port=dest["port"],
        )

        known_hosts_config = KnownHostsConfig(
            hostname=ssh["host"], fingerprint=ssh["fingerprint"]
        )

        return ssh_tunnel_config, known_hosts_config

    def create_ssh_config_file(self, config: SSHTunnelConfig) -> None:
        """
        Create an SSH configuration file

        Parameters
        ----------
        config: SSHTunnelConfig
            Contains the SSH tunnel configuration
        """
        log.debug("Creating SSH config file")

        # FIXME: This should not be a hard coded path

        environment = Environment(
            loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "node" / "template"),
            autoescape=True,
        )
        template = environment.get_template("ssh_config.j2")

        # inject template with vars
        ssh_config = template.render(**config._asdict())

        with open(self.config_folder / "config", "w") as f:
            f.write(ssh_config)

        # This is done also in the container, however vnode-local breaks
        # if we dont do it here
        os.chmod(self.config_folder / "config", 0o600)

    def create_known_hosts_file(self, config: KnownHostsConfig) -> None:
        """
        Create a known_hosts file

        Parameters
        ----------
        config: KnownHostsConfig
            Contains the fingerprint and hostname of the remote server
        """
        log.debug("Creating known_hosts file")
        log.debug(f"  Host: {config.hostname}")
        log.debug(f"  Fingerprint: {config.fingerprint}")
        with open(self.config_folder / "known_hosts", "w") as f:
            f.write(f"{config.hostname} {config.fingerprint}")

    def start(self) -> None:
        """
        Start an SSH tunnel container
        """
        assert self.ssh_tunnel_config, "SSH config not set"
        assert self.known_hosts_config, "Known hosts config not set"

        # Contains the (ssh) config and known_hosts file
        mounts = {
            self.config_volume: {"bind": "/root/.ssh", "mode": "rw"},
        }

        # Start the SSH tunnel container. We can do this prior connecting it
        # to the isolated network as the tunnel is not reliant on the network.
        log.debug("Starting SSH tunnel container")
        remove_container_if_exists(docker_client=self.docker, name=self.container_name)
        self.container = self.docker.containers.run(
            image=self.image,
            volumes=mounts,
            detach=True,
            name=self.container_name,
            command=self.ssh_tunnel_config.hostname,
            auto_remove=False,
            restart_policy={"Name": "always"},
        )

        # Connect to both the internal network and make an alias (=hostname).
        # This alias can be used by the algorithm containers.
        self.isolated_network_mgr.connect(self.container, aliases=[self.hostname])

    def stop(self) -> None:
        """
        Stop the SSH tunnel container
        """
        if not self.container:
            log.debug("SSH tunnel container not running")
            return

        remove_container(self.container, kill=True)
        log.info(f"SSH tunnel {self.hostname} stopped")
