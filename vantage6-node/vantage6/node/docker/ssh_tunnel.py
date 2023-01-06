"""
SSH Tunnel

This module contains the SSH tunnel class. It is responsible for creating
an SSH configuration file and starting an SSH tunnel container.

The SSH tunnel container is used to create a secure connection between the
private network of the node and an external data-source. This can then be used
by the algorithm containers to access the data-source. Multiple SSH tunnels
can be created, each with a different configuration.
"""
import logging

from typing import Union, Type, NamedTuple, Tuple
from enum import Enum
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from vantage6.common import logger_name
from vantage6.common.globals import APPNAME
from vantage6.node.docker.docker_base import DockerBaseManager
from vantage6.node.docker.docker_manager import NetworkManager
from vantage6.node.globals import SSH_TUNNEL_IMAGE

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


class SHHTunnelStatus(Enum):
    pass


class SSHTunnel(DockerBaseManager):

    def __init__(self, isolated_network_mgr: NetworkManager, config: dict,
                 node_name: str, tunnel_image: Union[str, None]) -> None:

        super().__init__(isolated_network_mgr)

        # reference to the SSH tunnel container
        self.container = None

        self.container_name = f"{APPNAME}-{node_name}-ssh-tunnel"

        # Place where we can store the SSH configuration file and the
        # known_hosts file.
        # FIXME: I think this should be a global setting, as this is mounted
        # by vantage6-CLI in the volume
        self.config_folder = Path("/mnt/configs")

        # Reference to isolated network, as we need to attach the SSH tunnel
        # container to this network
        self.isolated_network = isolated_network_mgr

        try:
            # hostname of the tunnel which can be used by the algorithm
            # containers
            self.hostname = config['hostname']
            log.debug(f"SSH tunnel hostname: {self.hostname}")

            # Create the SSH configuration, which can later be mounted by the
            # SSH tunnel container
            self.ssh_tunnel_config, self.known_hosts_config = \
                self.read_config(config)
        except KeyError as e:
            # parent class should handle this
            raise KeyError(f"Invalid SSH tunnel configuration: {e}")

        # The image is overridable by the user configuration
        self.image = tunnel_image if tunnel_image else SSH_TUNNEL_IMAGE
        log.debug(f"SSH tunnel image: {self.image}")

        # Create the SSH configuration files
        self.create_ssh_config_file(self.ssh_tunnel_config)
        self.create_known_hosts_file(self.known_hosts_config)

        self.start()
        log.info(f"SSH tunnel {self.hostname} started")

    def read_config(self, config: dict) \
            -> Tuple[SSHTunnelConfig, KnownHostsConfig]:
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
        log.debug("Reading SSH tunnel configuration")
        bind = config['tunnel']['bind']
        ssh = config['ssh']
        identity = config['ssh']['identity']

        # SSH config to connect to the remote server
        # TODO check if the identity file exists, and is at the location
        # i feel its not now
        ssh_tunnel_config = SSHTunnelConfig(
            username=identity['username'],
            hostname=ssh['host'],
            port=ssh['port'],
            identity_file=identity['key'],
            local_port=config['tunnel']['dest']['port'],
            bind_ip=bind['ip'],
            bind_port=bind['port']
        )

        known_hosts_config = KnownHostsConfig(
            hostname=ssh['host'],
            fingerprint=ssh['fingerprint']
        )

        return ssh_tunnel_config, known_hosts_config

    def create_ssh_config_file(self, config: Type[SSHTunnelConfig]) -> None:
        """
        Create an SSH configuration file

        Parameters
        ----------
        config: SSHConfig
            Contains the SSH tunnel configuration
        """
        log.debug("Creating SSH config file")

        # FIXME: This should not be a hard coded path
        environment = Environment(
            loader=FileSystemLoader("vantage6-node/vantage6/node/template/")
        )
        template = environment.get_template("ssh_config.j2")

        # inject template with vars
        ssh_config = template.render(**config)

        with open(self.config_folder / "ssh_config", "w") as f:
            f.write(ssh_config)

    def create_known_hosts_file(self, config: Type[KnownHostsConfig]) -> None:
        """
        Create a known_hosts file

        Parameters
        ----------
        config : Type[KnownHostsConfig]
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
        assert self.config, "SSH config not set"

        mounts = {
            '/mnt/config/ssh_config':
                {'bind': '/root/.ssh/config', 'mode': 'ro'},
            '/mnt/config/known_hosts':
                {'bind': '/root/.ssh/known_hosts', 'mode': 'ro'},
        }

        # Start the SSH tunnel container. We can do this prior connecting it
        # to the isolated network as the tunnel is not reliant on the network.
        log.debug("Starting SSH tunnel container")
        self.container = self.docker.containers.run(
            image=self.image,
            volumes=mounts,
            detach=True,
            restart_policy={"Name": "always"},
            name=self.container_name,
            command=self.ssh_tunnel_config.hostname
        )

        # Connect to both the internal network and make an alias (=hostname).
        # This alias can be used by the algorithm containers.
        self.isolated_network_mgr.connect(self.container, alias=self.hostname)

    def stop(self) -> None:
        """
        Stop the SSH tunnel container
        """
        assert self.container, "No container to stop"
        log.debug("Trying to stop SSH tunnel container")
        self.container.stop()
        log.info(f"SSH tunnel {self.hostname} stopped")
