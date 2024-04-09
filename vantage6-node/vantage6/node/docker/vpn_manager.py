import docker
import logging
import json
import time
import ipaddress

from json.decoder import JSONDecodeError
from docker.models.containers import Container

from vantage6.common import logger_name
from vantage6.common.globals import APPNAME, VPN_CONFIG_FILE
from vantage6.common.docker.addons import (
    remove_container_if_exists,
    remove_container,
    pull_image,
)
from vantage6.common.docker.network_manager import NetworkManager
from vantage6.node.globals import (
    MAX_CHECK_VPN_ATTEMPTS,
    NETWORK_CONFIG_IMAGE,
    VPN_CLIENT_IMAGE,
    FREE_PORT_RANGE,
    DEFAULT_ALGO_VPN_PORT,
    ALPINE_IMAGE,
)
from vantage6.common.client.node_client import NodeClient
from vantage6.node.docker.docker_base import DockerBaseManager
from vantage6.node._version import major_minor


class VPNManager(DockerBaseManager):
    """
    Setup a VPN client in a Docker container and configure the network so that
    the VPN container can forward traffic to and from algorithm containers.
    """

    log = logging.getLogger(logger_name(__name__))

    def __init__(
        self,
        isolated_network_mgr: NetworkManager,
        node_name: str,
        node_client: NodeClient,
        vpn_volume_name: str,
        vpn_subnet: str,
        alpine_image: str | None = None,
        vpn_client_image: str | None = None,
        network_config_image: str | None = None,
    ) -> None:
        """
        Initializes a VPN manager instance

        Parameters
        ----------
        isolated_network_mgr: NetworkManager
            An object that manages the node's isolated network
        node_name: str
            The name of the node (from config)
        vpn_volume_name: str
            The name of the volume in which the VPN data resides
        vpn_subnet: str
            The IP mask of the VPN subnet
        alpine_image: str | None
            Name of alternative Alpine image to be used
        vpn_client_image: str | None
            Name of alternative VPN client image to be used
        network_config_image: str | None
            Name of alternative network config image to be used
        """
        super().__init__(isolated_network_mgr)

        self.vpn_client_container_name = f"{APPNAME}-{node_name}-vpn-client"
        self.vpn_volume_name = vpn_volume_name
        self.client = node_client
        self.subnet = vpn_subnet

        # get the proper versions of the VPN images
        self.alpine_image = (
            f"{ALPINE_IMAGE}:{major_minor}" if not alpine_image else alpine_image
        )
        self.vpn_client_image = (
            f"{VPN_CLIENT_IMAGE}:{major_minor}"
            if not vpn_client_image
            else vpn_client_image
        )
        self.network_config_image = (
            f"{NETWORK_CONFIG_IMAGE}:{major_minor}"
            if not network_config_image
            else network_config_image
        )

        self._update_images()

        self.log.debug("Used VPN images:")
        self.log.debug(f"  Alpine: {self.alpine_image}")
        self.log.debug(f"  Client: {self.vpn_client_image}")
        self.log.debug(f"  Config: {self.network_config_image}")

        self.has_vpn = False

    def _update_images(self) -> None:
        """Pulls the latest version of the VPN images"""
        self.log.info("Updating VPN images...")
        self.log.debug("Pulling Alpine image")
        pull_image(self.docker, self.alpine_image)
        self.log.debug("Pulling VPN client image")
        pull_image(self.docker, self.vpn_client_image)
        self.log.debug("Pulling network config image")
        pull_image(self.docker, self.network_config_image)
        self.log.info("Done updating VPN images")

    def connect_vpn(self) -> None:
        """
        Start VPN client container and configure network to allow
        algorithm-to-algoritm communication
        """
        if not self.subnet:
            self.log.warn("VPN subnet is not defined! Disabling VPN...")
            self.log.info(
                "Define the 'vpn_subnet' field in your configuration"
                " if you want to use VPN"
            )
            return
        elif not self._is_ipv4_subnet(self.subnet):
            self.log.error(
                f"VPN subnet {self.subnet} is not a valid subnet! " "Disabling VPN..."
            )
            return

        self.log.debug("Mounting VPN configuration file")
        # add volume containing OVPN config file
        data_path = "/mnt/vpn/"  # TODO obtain from DockerNodeContext
        volumes = {
            self.vpn_volume_name: {"bind": data_path, "mode": "rw"},
        }
        # set environment variables
        vpn_config = data_path + VPN_CONFIG_FILE
        env = {"VPN_CONFIG": vpn_config}

        # if a VPN container is already running, kill and remove it
        remove_container_if_exists(
            docker_client=self.docker, name=self.vpn_client_container_name
        )

        # start vpnclient
        self.log.debug("Starting VPN client container")
        self.vpn_client_container = self.docker.containers.run(
            image=self.vpn_client_image,
            command="",  # commands to run are already defined in docker image
            volumes=volumes,
            detach=True,
            environment=env,
            restart_policy={"Name": "always"},
            name=self.vpn_client_container_name,
            cap_add=["NET_ADMIN", "SYSLOG"],
            devices=["/dev/net/tun"],
        )

        # attach vpnclient to isolated network
        self.log.debug("Connecting VPN client container to isolated network")
        self.isolated_network_mgr.connect(
            container_name=self.vpn_client_container_name,
            aliases=[self.vpn_client_container_name],
        )

        # check successful initiation of VPN connection
        if self.has_connection():
            self.log.info("VPN client container was successfully started!")
        else:
            raise ConnectionError("VPN connection not established!")

        # send VPN IP address to server
        self.send_vpn_ip_to_server()

        # check that the VPN connection IP address is part of the subnet
        # defined in the node configuration. If not, the VPN connection would
        # not work.
        if not self._vpn_in_right_subnet():
            self.log.error(
                "The VPN subnet defined in the node configuration file does "
                "not match the VPN server subnet. Turning off VPN..."
            )
            self.exit_vpn(cleanup_host_rules=False)
            return

        # create network exception so that packet transfer between VPN network
        # and the vpn client container is allowed
        self.isolated_bridge = self._find_isolated_bridge()
        if not self.isolated_bridge:
            self.log.error(
                "Setting up VPN failed: could not find bridge "
                "interface of isolated network"
            )
            return
        self._configure_host_network()

    def has_connection(self) -> bool:
        """
        Return True if VPN connection is active

        Returns
        -------
        bool
            True if VPN connection is active, False otherwise
        """
        self.log.debug("Waiting for VPN connection. This may take a minute...")
        n_attempt = 0
        self.has_vpn = False
        while n_attempt < MAX_CHECK_VPN_ATTEMPTS:
            n_attempt += 1
            try:
                _, vpn_interface = self.vpn_client_container.exec_run(
                    "ip --json addr show dev tun0"
                )
                vpn_interface = json.loads(vpn_interface)
                self.has_vpn = True
                break
            except (JSONDecodeError, docker.errors.APIError):
                # JSONDecodeError if VPN is not setup yet, APIError if VPN
                # container is restarting (e.g. due to connection errors)
                time.sleep(1)
        return self.has_vpn

    def exit_vpn(self, cleanup_host_rules: bool = True) -> None:
        """
        Gracefully shutdown the VPN and clean up

        Parameters
        ----------
        cleanup_host_rules: bool, optional
            Whether or not to clear host configuration rules. Should be True
            if they have been created at the time this function runs.
        """
        if not self.has_vpn:
            return
        self.has_vpn = False
        self.log.debug("Stopping and removing the VPN client container")
        remove_container(self.vpn_client_container, kill=True)

        # clear VPN IP address from server
        self.send_vpn_ip_to_server()

        # Clean up host network changes. We have added two rules to the front
        # of the DOCKER-USER chain. We now execute more or less the same
        # commands, but with -D (delete) instead of -I (insert)
        if cleanup_host_rules:
            command = (
                'sh -c "'
                f"iptables -D DOCKER-USER -d {self.subnet} "
                f"-i {self.isolated_bridge} -j ACCEPT; "
                f"iptables -D DOCKER-USER -s {self.subnet} "
                f"-o {self.isolated_bridge} -j ACCEPT; "
                '"'
            )
            try:
                self._run_host_network_configure_cmd(command)
            except docker.errors.ContainerError:
                # This error usually occurs when the DOCKER-USER chain does not
                # exist. In these cases the host often uses `iptables-legacy`
                # instead of `iptables`. We try again with `iptables-legacy`
                # instead.
                # FIXME BvB 2023-08-22: This is a temporary fix. In future,
                # when iptables-legacy is hardly used anymore on host systems,
                # this fix should be removed.
                command = command.replace("iptables", "iptables-legacy")
                self._run_host_network_configure_cmd(command)

    def get_vpn_ip(self) -> str:
        """
        Get VPN IP address in VPN server namespace

        Returns
        -------
        str
            IP address assigned to VPN client container by VPN server
        """
        try:
            # use has_connection() to check if VPN is active. This function
            # also waits for a connection to be established, which is helpful
            # for unstable connections
            if self.has_connection():
                _, vpn_interface = self.vpn_client_container.exec_run(
                    "ip --json addr show dev tun0"
                )
                vpn_interface = json.loads(vpn_interface)
        except (JSONDecodeError, docker.errors.APIError):
            # JSONDecodeError if VPN is not setup yet, APIError if VPN
            # container is restarting (e.g. due to connection errors)
            raise ConnectionError("Could not get VPN IP: VPN is not connected!")
        return vpn_interface[0]["addr_info"][0]["local"]

    def send_vpn_ip_to_server(self) -> None:
        """
        Send VPN IP address to the server
        """
        node_id = self.client.whoami.id_
        if self.has_vpn:
            node_ip = self.get_vpn_ip()
            self.client.request(f"node/{node_id}", json={"ip": node_ip}, method="PATCH")
        else:
            # VPN is disconnected, send NULL IP address
            self.client.request(
                f"node/{node_id}", json={"clear_ip": True}, method="PATCH"
            )

    def forward_vpn_traffic(
        self, helper_container: Container, algo_image_name: str
    ) -> list[dict] | None:
        """
        Setup rules so that traffic is properly forwarded between the VPN
        container and the algorithm container (and its helper container)

        Parameters
        ----------
        algo_helper_container: Container
            Helper algorithm container
        algo_image_name: str
            Name of algorithm image that is run

        Returns
        -------
        list[dict] | None
            Description of each port on the VPN client that forwards traffic to
            the algo container. None if VPN is not set up.
        """
        ports = self._forward_traffic_to_algorithm(helper_container, algo_image_name)
        self._forward_traffic_from_algorithm(helper_container)
        return ports

    def _forward_traffic_from_algorithm(self, algo_helper_container: Container) -> None:
        """
        Direct outgoing algorithm container traffic to the VPN client container

        Parameters
        ----------
        algo_helper_container: Container
            Helper algorithm container
        """
        if not self.has_vpn:
            return  # ignore if VPN is not active
        vpn_local_ip = self.isolated_network_mgr.get_container_ip(
            self.vpn_client_container_name
        )
        if not vpn_local_ip:
            self.log.error("VPN client container not found, turning off VPN")
            self.has_vpn = False
            return

        network = "container:" + algo_helper_container.id

        # add IP route line to the algorithm container network
        cmd = f"ip route replace default via {vpn_local_ip}"
        self.docker.containers.run(
            image=self.alpine_image,
            network=network,
            cap_add="NET_ADMIN",
            command=cmd,
            remove=True,
        )

    def _forward_traffic_to_algorithm(
        self, algo_helper_container: Container, algo_image_name: str
    ) -> list[dict] | None:
        """
        Forward incoming traffic from the VPN client container to the
        algorithm container

        Parameters
        ----------
        algo_helper_container: Container
            Helper algorithm container
        algo_image_name: str
            Name of algorithm image that is run

        Returns
        -------
        list[dict] | None
            Description of each port on the VPN client that forwards traffic to
            the algo container. None if VPN is not set up.
        """
        if not self.has_vpn:
            return None  # no port assigned if no VPN is available

        # Get IP Address of the algorithm container
        self.log.debug("Getting IP address of algorithm container")
        algo_helper_container.reload()  # update attributes
        algo_ip = self.get_isolated_netw_ip(algo_helper_container)

        # Set ports at which algorithm containers receive traffic
        self.log.debug("Finding exposed ports of algorithm container")
        ports = self._find_exposed_ports(algo_image_name)

        # Find ports on VPN container that are already occupied
        cmd = (
            "sh -c "
            '"iptables -t nat -L PREROUTING -n | '
            "awk '{print $7}' | cut -c 5-\""
        )
        occupied_ports = self.vpn_client_container.exec_run(cmd=cmd)

        occupied_ports = occupied_ports.output.decode("utf-8")
        occupied_ports = occupied_ports.split("\n")
        occupied_ports = list(
            set([int(port) for port in occupied_ports if port.isdigit()])
        )
        self.log.debug(f"Occupied ports: {occupied_ports}")

        # take first available port
        vpn_client_port_options = set(FREE_PORT_RANGE) - set(occupied_ports)
        for port in ports:
            port_ = vpn_client_port_options.pop()
            self.log.debug(f"Assigning port {port_} to algorithm port")
            port["port"] = port_

        vpn_ip = self.get_vpn_ip()
        self.log.debug(f"VPN IP: {vpn_ip}")

        # Set up forwarding VPN traffic to algorithm container
        command = 'sh -c "'
        for port in ports:
            # Rule for directing external vpn traffic to algorithms
            command += (
                "iptables -t nat -A PREROUTING -i tun0 -p tcp "
                f'--dport {port["port"]} -j DNAT '
                f'--to {algo_ip}:{port["algo_port"]};'
            )

            # Rule for directing internal vpn traffic to algorithms
            command += (
                f"iptables -t nat -A PREROUTING -d {vpn_ip}/32 -p tcp "
                f'--dport {port["port"]} -j DNAT '
                f'--to {algo_ip}:{port["algo_port"]};'
            )

            # remove the algorithm ports from the dictionaries as these are no
            # longer necessary
            del port["algo_port"]
        command += '"'
        self.vpn_client_container.exec_run(command)

        return ports

    def _vpn_in_right_subnet(self) -> bool:
        """
        Check if the VPN connection is part of the subnet defined in the node
        configuration.

        Returns
        -------
        bool
            Whether the VPN IP address is part of the subnet or not
        """
        vpn_ip = self.get_vpn_ip()
        return ipaddress.ip_address(vpn_ip) in ipaddress.ip_network(self.subnet)

    def _find_exposed_ports(self, image: str) -> list[dict]:
        """
        Find which ports were exposed via the EXPOSE keyword in the dockerfile
        of the algorithm image. This port will be used for VPN traffic. If no
        port is specified, the default port is used

        Parameters
        ----------
        image: str
            Algorithm image name

        Returns
        -------
        list[dict]:
            List of ports forward VPN traffic to. For each port, a dictionary
            containing port number and label is given
        """
        default_ports = [{"algo_port": DEFAULT_ALGO_VPN_PORT, "label": None}]
        algo_image = self.docker.images.get(image)

        exposed_ports = []
        try:
            exposed_ports = algo_image.attrs["Config"]["ExposedPorts"]
        except KeyError:
            return default_ports

        # find any labels defined in the docker image
        labels = {}
        try:
            labels = algo_image.attrs["Config"]["Labels"]
        except KeyError:
            pass  # No labels found, ignore

        ports = []
        for port in exposed_ports:
            port = port[0 : port.find("/")]
            try:
                int(port)
            except ValueError:
                self.log.warn(
                    "Could not parse port specified in algorithm "
                    f"docker image {image}: {port}"
                )
            # get port label: this should be defined as 'p1234' for port 1234
            label = None
            if labels:
                label = labels.get("p" + port)
            if not label:
                self.log.warn(
                    f"No label defined in image for port {port}. "
                    "Algorithm will not be able to find the port "
                    "using the label!"
                )
            ports.append({"algo_port": port, "label": label})

        if not ports:
            self.log.warn(
                "None of the ports in the algorithm image could be parsed. "
                f"Using default port {DEFAULT_ALGO_VPN_PORT} instead"
            )

        return ports if ports else default_ports

    def _find_isolated_bridge(self) -> str:
        """
        Retrieve the linked network interface in the host namespace for
        network interface eth0 in the container namespace.

        Returns
        -------
        str
            The name of the network interface in the host namespace
        """
        # Get the isolated network interface and extract its link index
        isolated_interface = self._get_isolated_interface()
        if isolated_interface:
            link_index = self._get_link_index(isolated_interface)
        else:
            return None  # cannot setup host rules if link is not found

        # Get network config from host namespace
        host_interfaces = self.docker.containers.run(
            image=self.network_config_image,
            network="host",
            command=["ip", "--json", "addr"],
            remove=True,
        )
        host_interfaces = json.loads(host_interfaces)

        linked_interface = self._get_interface_from_idx(host_interfaces, link_index)
        bridge_interface = linked_interface["master"]
        return bridge_interface

    def _get_isolated_interface(self):
        """
        Get the isolated network interface

        Get all network descriptions from ip addr and match the isolated
        network's interface by VPN ip address: this should be the same in the
        VPN container's attributes and in the network interface
        """
        isolated_interface = None
        _, interfaces = self.vpn_client_container.exec_run("ip --json addr")
        interfaces = json.loads(interfaces)
        vpn_ip_isolated_netw = self.get_isolated_netw_ip(self.vpn_client_container)
        for ip_interface in interfaces:
            if self.is_isolated_interface(ip_interface, vpn_ip_isolated_netw):
                isolated_interface = ip_interface
        return isolated_interface

    @staticmethod
    def is_isolated_interface(ip_interface: dict, vpn_ip_isolated_netw: str) -> bool:
        """
        Return True if a network interface is the isolated network
        interface. Identify this based on the IP address of the VPN client in
        the isolated network

        Parameters
        ----------
        ip_interface: dict
            IP interface obtained by executing `ip --json addr` command
        vpn_ip_isolated_netw: str
            IP address of VPN container in isolated network

        Returns
        -------
        bool
            True if this is the interface describing the isolated network
        """
        # check if attributes exist in json: if not then it is not the right
        # interface
        if (
            "addr_info" in ip_interface
            and len(ip_interface["addr_info"])
            and "local" in ip_interface["addr_info"][0]
        ):
            # Right attributes are present: check if IP addresses match
            return vpn_ip_isolated_netw == ip_interface["addr_info"][0]["local"]
        else:
            return False

    def _configure_host_network(self) -> None:
        """
        By default the internal bridge networks are configured to prohibit
        packet forwarding between networks. Create an exception to this rule
        for forwarding traffic between the bridge and vpn network.
        """
        self.log.debug("Configuring host network exceptions for VPN")
        # The following command inserts rules that traffic from the VPN subnet
        # will be accepted into the isolated network
        command = (
            'sh -c "'
            f"iptables -I DOCKER-USER 1 -d {self.subnet} "
            f"-i {self.isolated_bridge} -j ACCEPT; "
            f"iptables -I DOCKER-USER 1 -s {self.subnet} "
            f"-o {self.isolated_bridge} -j ACCEPT; "
            '"'
        )

        try:
            self._run_host_network_configure_cmd(command)
        except docker.errors.ContainerError:
            # This error usually occurs when the DOCKER-USER chain does not
            # exist. In these cases the host often uses `iptables-legacy`
            # instead of `iptables`. We try again with `iptables-legacy`
            # instead.
            # FIXME BvB 2023-08-22: This is a temporary fix. In future,
            # when iptables-legacy is hardly used anymore on host systems,
            # this fix should be removed.
            command = command.replace("iptables", "iptables-legacy")
            self._run_host_network_configure_cmd(command)

    def _run_host_network_configure_cmd(self, cmd: str) -> None:
        """
        Run a command to configure the host network

        Parameters
        ----------
        cmd: str
            Command to run
        """
        self.docker.containers.run(
            image=self.network_config_image,
            network="host",
            cap_add="NET_ADMIN",
            command=cmd,
            remove=True,
        )

    @staticmethod
    def _get_interface_from_idx(interfaces: list[dict], index: int) -> dict | None:
        """
        Get interface configuration based on interface index

        Parameters
        ----------
        interfaces: list
            List of interfaces as returned by `ip --json addr`
        index: int
            Interface index

        Returns
        -------
        dict | None
            Interface configuration or None if not found
        """
        for interface in interfaces:
            if int(interface["ifindex"]) == index:
                return interface

        return None

    @staticmethod
    def _get_link_index(if_json: dict | list) -> int:
        """
        Get the link index of an interface

        Parameters
        ----------
        if_json: dict | list
            Interface configuration as returned by `ip --json addr`

        Returns
        -------
        int
            Link index of the interface
        """
        if isinstance(if_json, list):
            if_json = if_json[-1]
        return int(if_json["link_index"])

    def _is_ipv4_subnet(self, subnet: str) -> bool:
        """
        Validate if subnet has format '12.34.56.78/16'

        Parameters
        ----------
        subnet: str
            Subnet to validate

        Returns
        -------
        bool
            True if subnet is valid
        """
        parts = subnet.split("/")
        if len(parts) != 2:
            return False
        if not parts[1].isdigit() or int(parts[1]) > 32:
            return False
        octets = parts[0].split(".")
        return len(octets) == 4 and all(
            o.isdigit() and 0 <= int(o) < 256 for o in octets
        )
