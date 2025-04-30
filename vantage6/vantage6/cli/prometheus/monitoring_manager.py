from vantage6.cli.context.server import ServerContext
from vantage6.common.docker.network_manager import NetworkManager
from vantage6.server.globals import DEFAULT_PROMETHEUS_EXPORTER_PORT
import yaml
import docker
from pathlib import Path
from vantage6.cli.globals import (
    DEFAULT_PROMETHEUS_IMAGE,
    PROMETHEUS_CONFIG,
)
from vantage6.common import info, error


class PrometheusServer:
    """
    Manages the Prometheus Docker container
    """

    def __init__(
        self, ctx: ServerContext, network_mgr: NetworkManager, image: str = None
    ):
        """
        Initialize the PrometheusServer instance.

        Parameters
        ----------
        ctx : ServerContext
            The server context containing configuration and paths.
        network_mgr : NetworkManager
            The network manager responsible for managing Docker networks.
        image : str, optional
            The Docker image to use for the Prometheus container. If not provided,
            the default Prometheus image will be used.
        """
        self.ctx = ctx
        self.network_mgr = network_mgr
        self.docker = docker.from_env()
        self.image = image if image else DEFAULT_PROMETHEUS_IMAGE
        self.config_file = Path(self.ctx.data_dir / PROMETHEUS_CONFIG)
        self.data_dir = self.ctx.prometheus_dir

    def start(self):
        """
        Start a Docker container running Prometheus
        """
        self._prepare_config()

        volumes = {
            str(self.config_file): {
                "bind": "/etc/prometheus/prometheus.yml",
                "mode": "ro",
            },
            str(self.data_dir): {"bind": "/prometheus", "mode": "rw"},
        }
        ports = {"9090/tcp": 9090}

        container = self._get_container()
        if container:
            info("Prometheus is already running!")
            return

        self.docker.containers.run(
            name=self.ctx.prometheus_container_name,
            image=self.image,
            volumes=volumes,
            ports=ports,
            detach=True,
            restart_policy={"Name": "unless-stopped"},
            network=self.network_mgr.network_name,
        )
        info("Prometheus container started successfully!")

    def _prepare_config(self):
        """
        Prepare the Prometheus configuration and data directories
        """
        if not self.config_file.exists():
            error(f"Prometheus configuration file {self.config_file} not found!")
            raise FileNotFoundError(f"{self.config_file} not found!")

        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)

        self._update_prometheus_config()

    def _update_prometheus_config(self):
        """
        Update the Prometheus configuration file with the server address.
        """

        try:
            prometheus_exporter_port = self.ctx.config.get("prometheus", {}).get(
                "exporter_port", DEFAULT_PROMETHEUS_EXPORTER_PORT
            )
            server_hostname = self.ctx.prometheus_container_name
            server_address = f"{server_hostname}:{prometheus_exporter_port}"

            with open(self.config_file, "r") as f:
                config = yaml.safe_load(f)

            job_name = "vantage6_server_metrics"
            job_exists = any(
                job.get("job_name") == job_name
                for job in config.get("scrape_configs", [])
            )

            if not job_exists:
                new_job = {
                    "job_name": job_name,
                    "static_configs": [{"targets": [server_address]}],
                }
                config.setdefault("scrape_configs", []).append(new_job)
            else:
                for job in config["scrape_configs"]:
                    if job.get("job_name") == job_name:
                        job["static_configs"] = [{"targets": [server_address]}]

            with open(self.config_file, "w") as f:
                yaml.dump(config, f)

            info(f"Prometheus configuration updated with target: {server_address}")

        except Exception as e:
            error(f"Failed to update Prometheus configuration: {e}")
            raise

    def _get_container(self) -> docker.models.containers.Container | None:
        """
        Check if a Prometheus container is already running.

        Returns
        -------
        docker.models.containers.Container or None
            The Prometheus container object if it is running, or None if no such container exists.
        """
        try:
            return self.docker.containers.get(self.ctx.docker_container_name)
        except docker.errors.NotFound:
            return None
