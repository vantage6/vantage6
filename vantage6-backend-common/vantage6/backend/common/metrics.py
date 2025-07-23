import logging
from typing import Any, Type
from prometheus_client import Gauge, start_http_server

log = logging.getLogger(__name__)


class Metric:
    """
    Represents a single metric with its name, expected type, and description.
    """

    def __init__(self, name: str, type_: Type[Any], description: str):
        self.name = name
        self.type = type_
        self.description = description


class Metrics:
    """
    Class to manage all system metrics and their Prometheus gauges.
    """

    def __init__(self, labels: list[str]):
        """
        Initialize the Metrics class and create Prometheus gauges.

        Parameters
        ----------
        labels: list[str]
            List of labels to be used for all metrics.
        """
        self.labels = labels
        self.gauges = {}
        self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """
        Define all system metrics and create their corresponding Prometheus gauges.
        """
        metrics = [
            Metric("cpu_percent", float, "CPU usage percentage"),
            Metric("memory_percent", float, "Memory usage percentage"),
            Metric(
                "num_algorithm_containers",
                int,
                "Number of running algorithm containers",
            ),
            Metric("cpu_count", int, "Number of CPUs"),
            Metric("memory_total", int, "Total memory"),
            Metric("memory_available", int, "Available memory"),
            Metric("gpu_count", int, "Number of GPUs"),
            Metric("gpu_load", float, "GPU load"),
            Metric("gpu_memory_used", int, "GPU memory used"),
            Metric("gpu_memory_free", int, "GPU memory free"),
            Metric("gpu_temperature", float, "GPU temperature"),
        ]

        for metric in metrics:
            if "gpu" in metric.name:
                self.gauges[metric.name] = Gauge(
                    metric.name, metric.description, labelnames=self.labels + ["gpu_id"]
                )
            else:
                self.gauges[metric.name] = Gauge(
                    metric.name, metric.description, labelnames=self.labels
                )

    def set_metric(self, metric_name: str, value: Any, labels: dict) -> None:
        """
        Set the value of a metric, handling GPU-specific logic if necessary.

        Parameters
        ----------
        metric_name: str
            The name of the metric to set.
        value: Any
            The value to set for the metric.
        labels: dict
            A dictionary of labels to apply to the metric.
        """
        if metric_name not in self.gauges:
            raise ValueError(f"Metric '{metric_name}' does not exist.")

        gauge = self.gauges[metric_name]

        if "gpu" in metric_name:
            # GPU metrics must be lists
            if not isinstance(value, list):
                raise ValueError(
                    f"Expected a list for GPU metric '{metric_name}', got {type(value).__name__}."
                )
            for gpu_id, gpu_value in enumerate(value):
                gauge.labels(**labels, gpu_id=gpu_id).set(gpu_value)
        else:
            # Non-GPU metrics
            gauge.labels(**labels).set(value)

    def get_gauge(self, metric_name: str) -> Gauge:
        """
        Retrieve the Prometheus gauge for a given metric.

        Parameters
        ----------
        metric_name: str
            The name of the metric.

        Returns
        -------
        Gauge
            The Prometheus gauge for the metric.
        """
        if metric_name not in self.gauges:
            raise ValueError(f"Metric '{metric_name}' does not exist.")
        return self.gauges[metric_name]


def start_prometheus_exporter(port: int = 9100) -> None:
    """
    Start the Prometheus exporter to expose metrics.
    """
    log.info("Initializing Prometheus exporter...")
    try:
        start_http_server(port)
        log.info("Prometheus exporter started on port %s", port)
    except Exception as e:
        log.error("Failed to start Prometheus exporter: %s", e)
