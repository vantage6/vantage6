from pathlib import Path

from vantage6.common.globals import HTTP_LOCALHOST, InstanceType, Ports

from vantage6.cli.common.new import new
from vantage6.cli.sandbox.config.base import BaseSandboxConfigManager


class CoreSandboxConfigManager(BaseSandboxConfigManager):
    """
    Class to store the sandbox configurations.

    Parameters
    ----------
    server_name : str
        Name of the server.
    server_port : int
        Port of the server.
    ui_port : int
        Port of the UI.
    algorithm_store_port : int
        Port of the algorithm store.
    server_image : str | None
        Image of the server.
    store_image : str | None
        Image of the algorithm store.
    ui_image : str | None
        Image of the UI.
    extra_server_config : Path | None
        Path to the extra server configuration file.
    extra_store_config : Path | None
        Path to the extra algorithm store configuration file.
    context : str | None
        Kubernetes context.
    namespace : str | None
        Kubernetes namespace.
    k8s_node_name : str
        Kubernetes node name.
    custom_data_dir : Path | None
        Path to the custom data directory. Useful on WSL because of mount issues for
        default directories.
    """

    def __init__(
        self,
        server_name: str,
        server_port: int,
        ui_port: int,
        algorithm_store_port: int,
        server_image: str | None,
        store_image: str | None,
        ui_image: str | None,
        extra_server_config: Path | None,
        extra_store_config: Path | None,
        extra_auth_config: Path | None,
        context: str,
        namespace: str,
        k8s_node_name: str,
        custom_data_dir: Path | None = None,
    ) -> None:
        super().__init__(server_name, custom_data_dir)

        self.server_port = server_port
        self.ui_port = ui_port
        self.algorithm_store_port = algorithm_store_port
        self.server_image = server_image
        self.store_image = store_image
        self.ui_image = ui_image
        self.extra_server_config = extra_server_config
        self.extra_store_config = extra_store_config
        self.extra_auth_config = extra_auth_config
        self.context = context
        self.namespace = namespace

        self.server_config_file = None
        self.store_config_file = None
        self.auth_config_file = None
        self.k8s_node_name = k8s_node_name

    def generate_server_configs(self) -> None:
        """Generates the demo network."""

        self._create_auth_config()

        self._create_vserver_config()

        self._create_algo_store_config()

    def __server_config_return_func(self, extra_config: dict, data_dir: Path) -> dict:
        """
        Return a dict with server configuration values to be used in creating the
        config file.

        Parameters
        ----------
        extra_config : dict
            Extra configuration (parsed from YAML) to be added to the server
            configuration.
        data_dir : Path
            Path to the data directory.

        Returns
        -------
        dict
            Dictionary with server configuration values.
        """
        store_service = (
            f"vantage6-{self.server_name}-store-user-algorithm-store-store-service"
        )
        store_address = (
            f"http://{store_service}.{self.namespace}.svc.cluster.local:"
            f"{Ports.DEV_ALGO_STORE}"
        )
        config = {
            "server": {
                "baseUrl": f"{HTTP_LOCALHOST}:{self.server_port}",
                # TODO: v5+ set to latest v5 image
                # TODO make this configurable
                "image": (
                    self.server_image
                    or "harbor2.vantage6.ai/infrastructure/server:5.0.0a36"
                ),
                "algorithm_stores": [
                    {
                        "name": "Local store",
                        "url": store_address,
                        "api_path": "/store",
                    }
                ],
                "logging": {
                    "level": "DEBUG",
                },
                "jwt": {
                    "secret": "development-constant-secret!",
                },
                "dev": {
                    "host_uri": (
                        "host.docker.internal"
                        if self.k8s_node_name == "docker-desktop"
                        else "172.17.0.1"
                    ),
                    "store_address": store_address,
                },
                "keycloakUrl": (
                    f"http://vantage6-{self.server_name}-auth-user-auth-keycloak."
                    f"{self.namespace}.svc.cluster.local"
                ),
            },
            "rabbitmq": {},
            "database": {
                "volumePath": str(data_dir),
                "k8sNodeName": self.k8s_node_name,
            },
            "ui": {
                "port": self.ui_port,
                # TODO: v5+ set to latest v5 image
                # TODO: make this configurable
                "image": (
                    self.ui_image or "harbor2.vantage6.ai/infrastructure/ui:5.0.0a36"
                ),
            },
        }

        # merge the extra config with the server config
        if extra_config is not None:
            config.update(extra_config)

        return config

    def _create_vserver_config(self) -> None:
        """Creates server configuration file (YAML)."""

        data_dir = self._create_and_get_data_dir(instance_type=InstanceType.SERVER)

        extra_config = self._read_extra_config_file(self.extra_server_config)
        if self.ui_image is not None:
            ui_config = extra_config.get("ui", {}) if extra_config is not None else {}
            ui_config["image"] = self.ui_image
            extra_config["ui"] = ui_config

        # Create the server config file
        self.server_config_file = new(
            config_producing_func=self.__server_config_return_func,
            config_producing_func_args=(extra_config, data_dir),
            name=self.server_name,
            system_folders=False,
            namespace=self.namespace,
            context=self.context,
            type_=InstanceType.SERVER,
            is_sandbox=True,
        )

    def _create_algo_store_config(self) -> None:
        """Create algorithm store configuration file (YAML)."""

        extra_config = self._read_extra_config_file(self.extra_store_config)

        data_dir = self._create_and_get_data_dir(InstanceType.ALGORITHM_STORE)

        self.store_config_file = new(
            config_producing_func=self.__algo_store_config_return_func,
            config_producing_func_args=(extra_config, data_dir),
            name=f"{self.server_name}-store",
            system_folders=False,
            namespace=self.namespace,
            context=self.context,
            type_=InstanceType.ALGORITHM_STORE,
            is_sandbox=True,
        )

    def __algo_store_config_return_func(
        self, extra_config: dict, data_dir: Path
    ) -> dict:
        """
        Return a dict with algorithm store configuration values to be used in creating
        the config file.

        Returns
        -------
        dict
            Dictionary with algorithm store configuration values.
        """
        config = {
            "store": {
                "internal": {
                    "port": self.algorithm_store_port,
                },
                "logging": {
                    "level": "DEBUG",
                },
                "vantage6ServerUri": f"{HTTP_LOCALHOST}:{self.server_port}",
                "image": (
                    self.store_image
                    or "harbor2.vantage6.ai/infrastructure/algorithm-store:5.0.0a36"
                ),
                "keycloakUrl": (
                    f"http://vantage6-{self.server_name}-auth-user-auth-keycloak."
                    f"{self.namespace}.svc.cluster.local"
                ),
                "policies": {
                    "allowLocalhost": True,
                    "assignReviewOwnAlgorithm": True,
                },
                "dev": {
                    "host_uri": (
                        "host.docker.internal"
                        if self.k8s_node_name == "docker-desktop"
                        else "172.17.0.1"
                    ),
                    "disable_review": True,
                    "review_own_algorithm": True,
                },
            },
            "database": {
                "volumePath": str(data_dir),
                "k8sNodeName": self.k8s_node_name,
            },
        }

        # merge the extra config with the algorithm store config
        if extra_config is not None:
            config.update(extra_config)

        return config

    def _create_auth_config(self) -> None:
        """Create auth configuration file (YAML)."""
        self.auth_config_file = new(
            config_producing_func=self.__auth_config_return_func,
            config_producing_func_args=(self.extra_auth_config,),
            name=f"{self.server_name}-auth",
            system_folders=False,
            namespace=self.namespace,
            context=self.context,
            type_=InstanceType.AUTH,
            is_sandbox=True,
        )

    def __auth_config_return_func(self, extra_config: dict) -> dict:
        """
        Return a dict with auth configuration values to be used in creating the
        config file.
        """

        config = {
            "keycloak": {
                "production": False,
                "no_password_update_required": True,
                "redirectUris": [
                    f"{HTTP_LOCALHOST}:7600",
                    f"{HTTP_LOCALHOST}:7681",
                ],
            },
        }

        # merge the extra config with the auth config
        if extra_config is not None:
            config.update(extra_config)

        return config
