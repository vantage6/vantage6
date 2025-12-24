from pathlib import Path

from vantage6.common.globals import HTTP_LOCALHOST, InstanceType, Ports

from vantage6.cli.common.new import new
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.sandbox.config.base import BaseSandboxConfigManager


class SandboxHubConfigManager(BaseSandboxConfigManager):
    """
    Class to store the sandbox configurations.

    Parameters
    ----------
    hq_name : str
        Name of the HQ.
    hq_image : str | None
        Image of the HQ.
    store_image : str | None
        Image of the algorithm store.
    ui_image : str | None
        Image of the UI.
    extra_hq_config : Path | None
        Path to the extra HQ configuration file.
    extra_store_config : Path | None
        Path to the extra algorithm store configuration file.
    k8s_config : KubernetesConfig
        Kubernetes configuration.
    custom_data_dir : Path | None
        Path to the custom data directory. Useful on WSL because of mount issues for
        default directories.
    """

    def __init__(
        self,
        hq_name: str,
        hq_image: str | None,
        store_image: str | None,
        ui_image: str | None,
        extra_hq_config: Path | None,
        extra_store_config: Path | None,
        extra_auth_config: Path | None,
        k8s_config: KubernetesConfig,
        with_prometheus: bool = False,
        custom_data_dir: Path | None = None,
    ) -> None:
        super().__init__(hq_name, custom_data_dir)

        self.hq_image = hq_image
        self.store_image = store_image
        self.ui_image = ui_image
        self.extra_hq_config = extra_hq_config
        self.extra_store_config = extra_store_config
        self.extra_auth_config = extra_auth_config
        self.k8s_config = k8s_config
        self.with_prometheus = with_prometheus

    def generate_hq_configs(self) -> None:
        """Generates the local sandbox network."""

        self._create_auth_config()

        self._create_hq_config()

        self._create_algo_store_config()

    def __hq_config_return_func(
        self,
        extra_config: dict,
    ) -> dict:
        """
        Return a dict with HQ configuration values to be used in creating the
        config file.

        Parameters
        ----------
        extra_config : dict
            Extra configuration (parsed from YAML) to be added to the HQ
            configuration.

        Returns
        -------
        dict
            Dictionary with HQ configuration values.
        """
        data_dir = self._create_and_get_data_dir(instance_type=InstanceType.HQ)

        log_dir = self._create_and_get_data_dir(InstanceType.HQ, is_log_dir=True)

        prometheus_config = {
            "enabled": self.with_prometheus,
        }
        if self.with_prometheus:
            prometheus_dir = self._create_and_get_data_dir(
                InstanceType.HQ, custom_folder="prometheus"
            )
            prometheus_config.update(
                {
                    "exporter_port": Ports.SANDBOX_PROMETHEUS.value,
                    "storageSize": "2Gi",
                    "storageClass": "local-storage",
                    "volumeHostPath": prometheus_dir,
                }
            )

        store_service = f"vantage6-{self.hq_name}-store-user-algorithm-store"
        store_address = (
            f"http://{store_service}.{self.k8s_config.namespace}.svc.cluster.local"
            f":{Ports.SANDBOX_ALGO_STORE.value}"
        )
        config = {
            "hq": {
                "baseUrl": f"{HTTP_LOCALHOST}:{Ports.SANDBOX_HQ.value}",
                "port": Ports.SANDBOX_HQ.value,
                "internal": {
                    "port": Ports.SANDBOX_HQ.value,
                },
                "image": (
                    self.hq_image or "harbor2.vantage6.ai/infrastructure/hq:uluru"
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
                    "volumeHostPath": log_dir,
                },
                "jwt": {
                    "secret": "development-constant-secret!",
                },
                "dev": {
                    "host_uri": (
                        "host.docker.internal"
                        if self.k8s_config.k8s_node == "docker-desktop"
                        else "172.17.0.1"
                    ),
                    "store_address": store_address,
                    "forward_ports": True,
                    "local_hub_port_to_expose": Ports.SANDBOX_HQ.value,
                    "local_ui_port_to_expose": Ports.SANDBOX_UI.value,
                },
                "keycloak": {
                    "url": (
                        f"http://vantage6-{self.hq_name}-auth-user-auth-kc-service."
                        f"{self.k8s_config.namespace}.svc.cluster.local:8080"
                    ),
                },
            },
            "rabbitmq": {},
            "database": {
                "volumePath": data_dir,
                "k8sNodeName": self.k8s_config.k8s_node,
            },
            "ui": {
                "port": Ports.SANDBOX_UI.value,
                "image": (
                    self.ui_image or "harbor2.vantage6.ai/infrastructure/ui:uluru"
                ),
                "keycloak": {
                    "publicUrl": f"http://localhost:{Ports.SANDBOX_AUTH.value}",
                },
            },
            "prometheus": prometheus_config,
        }

        if self.with_prometheus:
            config["hq"]["dev"]["local_prometheus_port_to_expose"] = (
                Ports.SANDBOX_PROMETHEUS.value
            )

        # merge the extra config with the HQ config
        if extra_config is not None:
            config.update(extra_config)

        return config

    def _create_hq_config(self) -> None:
        """Creates HQ configuration file (YAML)."""

        extra_config = self._read_extra_config_file(self.extra_hq_config)
        if self.ui_image is not None:
            ui_config = extra_config.get("ui", {}) if extra_config is not None else {}
            ui_config["image"] = self.ui_image
            extra_config["ui"] = ui_config

        # Create the HQ config file
        new(
            config_producing_func=self.__hq_config_return_func,
            config_producing_func_args=(extra_config,),
            name=self.hq_name,
            system_folders=False,
            type_=InstanceType.HQ,
            is_sandbox=True,
        )

    def _create_algo_store_config(self) -> None:
        """Create algorithm store configuration file (YAML)."""

        extra_config = self._read_extra_config_file(self.extra_store_config)

        data_dir = self._create_and_get_data_dir(InstanceType.ALGORITHM_STORE)
        log_dir = self._create_and_get_data_dir(
            InstanceType.ALGORITHM_STORE, is_log_dir=True
        )

        new(
            config_producing_func=self.__algo_store_config_return_func,
            config_producing_func_args=(extra_config, data_dir, log_dir),
            name=f"{self.hq_name}-store",
            system_folders=False,
            type_=InstanceType.ALGORITHM_STORE,
            is_sandbox=True,
        )

    def __algo_store_config_return_func(
        self, extra_config: dict, data_dir: str, log_dir: str
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
                "baseUrl": f"{HTTP_LOCALHOST}:{Ports.SANDBOX_ALGO_STORE.value}",
                "internal": {
                    "port": Ports.SANDBOX_ALGO_STORE.value,
                },
                "port": Ports.SANDBOX_ALGO_STORE.value,
                "logging": {
                    "level": "DEBUG",
                    "volumeHostPath": log_dir,
                },
                "vantage6HQUri": f"{HTTP_LOCALHOST}:{Ports.SANDBOX_HQ.value}",
                "image": (
                    self.store_image
                    or "harbor2.vantage6.ai/infrastructure/algorithm-store:uluru"
                ),
                "keycloak": {
                    "url": (
                        f"http://vantage6-{self.hq_name}-auth-user-auth-kc-service."
                        f"{self.k8s_config.namespace}.svc.cluster.local:8080"
                    ),
                },
                "policies": {
                    "allowLocalhost": True,
                    "assignReviewOwnAlgorithm": True,
                },
                "dev": {
                    "host_uri": (
                        "host.docker.internal"
                        if self.k8s_config.k8s_node == "docker-desktop"
                        else "172.17.0.1"
                    ),
                    "disable_review": True,
                    "review_own_algorithm": True,
                    "forward_ports": True,
                    "local_port_to_expose": Ports.SANDBOX_ALGO_STORE.value,
                },
            },
            "database": {
                "volumePath": data_dir,
                "k8sNodeName": self.k8s_config.k8s_node,
            },
        }

        # merge the extra config with the algorithm store config
        if extra_config is not None:
            config.update(extra_config)

        return config

    def _create_auth_config(self) -> None:
        """Create auth configuration file (YAML)."""
        new(
            config_producing_func=self.__auth_config_return_func,
            config_producing_func_args=(self.extra_auth_config,),
            name=f"{self.hq_name}-auth",
            system_folders=False,
            type_=InstanceType.AUTH,
            is_sandbox=True,
        )

    def __auth_config_return_func(self, extra_config: dict) -> dict:
        """
        Return a dict with auth configuration values to be used in creating the
        config file.
        """

        data_dir = self._create_and_get_data_dir(InstanceType.AUTH)

        config = {
            "keycloak": {
                "production": False,
                "no_password_update_required": True,
                "redirectUris": [
                    f"{HTTP_LOCALHOST}:{Ports.SANDBOX_UI.value}",
                    f"{HTTP_LOCALHOST}:7681",
                ],
            },
            "database": {
                "volumePath": data_dir,
                "k8sNodeName": self.k8s_config.k8s_node,
            },
        }

        # merge the extra config with the auth config
        if extra_config is not None:
            config.update(extra_config)

        return config
