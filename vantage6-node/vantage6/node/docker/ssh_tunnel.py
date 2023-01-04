"""
SSH Tunnel

This module contains the SSH tunnel class. It is responsible for creating
an SSH configuration file and starting an SSH tunnel container.

The SSH tunnel container is used to create a secure connection between the
private network of the node and an external data-source. This can then be used
by the algorithm containers to access the data-source. Multiple SSH tunnels
can be created, each with a different configuration.
"""
from typing import Union, Tuple, Type
from dataclasses import dataclass

from vantage6.node.docker.docker_base import DockerBaseManager
from vantage6.node.docker.docker_manager import NetworkManager
from vantage6.node.globals import SSH_TUNNEL_IMAGE

@dataclass
class SSHIdentity:
    username: str
    password: str
    key: str

@dataclass
class Address:
    host: str
    port: int

@dataclass
class SSHDestination(Address):
    fingerprint: str

@dataclass
class SSHConfig:
    bind: Type[Address]
    dest: Type[SSHDestination]
    identity: Type[SSHIdentity]


class SSHTunnel(DockerBaseManager):

    def __init__(self, isolated_network_mgr: NetworkManager, config: dict,
                 config_volume: str, tunnel_image: Union[str, None] = None
                 ) -> None:

        super().__init__(isolated_network_mgr)

        # reference to isolated network, as we need to attach the SSH tunnel
        # container to this network
        self.isolated_network = isolated_network_mgr

        # contains the SSH configuration, but also the hostname and port of the
        # SSH tunnel container, which is used by the algorithm containers
        self.ssh_config = self.read_config(config)

        # The image is overridable by the user configuration
        self.image = tunnel_image if tunnel_image else SSH_TUNNEL_IMAGE

        # Extract the SSH configuration from the config and store it in a file
        # that can be used by the SSH tunnel container
        self.create_ssh_config_file(self.ssh_config)

        # reference to the SSH tunnel container
        self.container = None

    def read_config(self, config: dict) -> SSHConfig:
        """
        Read the SSH configuration from the config

        Parameters
        ----------
        config: dict
            Dictionary containing the SSH configuration

        Returns
        -------
        SSHConfig
            SSH configuration
        """
        if not all(key in config for key in ['bind', 'dest', 'identity']):
            raise ValueError("SSH config is missing keys")

        bind = config['bind']
        if not all(key in bind for key in ['host', 'port']):
            raise ValueError("SSH bind config is missing keys")

        dest = config['dest']
        if not all(key in dest for key in ['host', 'port', 'fingerprint']):
            raise ValueError("SSH dest config is missing keys")

        identity = config['identity']
        if not all(key in identity for key in ['username',
                'password', 'key']):
            raise ValueError("SSH identity config is missing keys")

        return SSHConfig(
            bind=Address(**bind),
            dest=SSHDestination(**dest),
            identity=SSHIdentity(**identity)
        )

    def create_ssh_config_file(self, config: SSHConfig) -> None:
        """
        Create an SSH configuration file and store it in a volume that can be
        accessed by the SSH tunnel container

        Parameters
        ----------
        config: SSHConfig
            Contains the SSH tunnel configuration
        """
        # Create SSH config file
        pass

    def start(self) -> None:
        """
        Start an SSH tunnel container
        """
        assert self.config, "SSH config not set"

        self.container = self.docker.containers.run(
            image=SSH_TUNNEL_IMAGE,

        )

        # connect to both the internal network

        self.isolated_network_mgr.connect(self.container, alias="ssh_tunnel")

        # create tunnel
        self.container.exec_run(
            f"ssh -N -f -L {self.config['port']}:"
        )

    def stop(self) -> None:
        """
        Stop the SSH tunnel container
        """
        assert self.container, "No container to stop"
        self.container.stop()
