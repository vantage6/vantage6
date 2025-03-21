from dataclasses import dataclass, fields
import logging
from typing import Any, Optional, Type
from prometheus_client import Gauge, start_http_server


@dataclass
class Metric:
    """
    Represents a single metric with its name, expected type and description.
    """

    name: str
    type: Type[Any]
    description: str


@dataclass
class Metrics:
    """
    Dataclass to define all system metrics with their names and expected types.
    """

    CPU_PERCENT: Metric = Metric(
        name="cpu_percent", type=float, description="CPU usage percentage"
    )
    MEMORY_PERCENT: Metric = Metric(
        name="memory_percent", type=float, description="Memory usage percentage"
    )
    NUM_ALGORITHM_CONTAINERS: Metric = Metric(
        name="num_algorithm_containers",
        type=int,
        description="Number of running algorithm containers",
    )
    OS: Metric = Metric(name="os", type=str, description="Operating system")
    PLATFORM: Metric = Metric(name="platform", type=str, description="Platform")
    CPU_COUNT: Metric = Metric(name="cpu_count", type=int, description="Number of CPUs")
    MEMORY_TOTAL: Metric = Metric(
        name="memory_total", type=int, description="Total memory"
    )
    MEMORY_AVAILABLE: Metric = Metric(
        name="memory_available", type=int, description="Available memory"
    )
    GPU_COUNT: Optional[Metric] = Metric(
        name="gpu_count", type=int, description="Number of GPUs"
    )
    GPU_LOAD: Optional[Metric] = Metric(
        name="gpu_load", type=float, description="GPU load"
    )
    GPU_MEMORY_USED: Optional[Metric] = Metric(
        name="gpu_memory_used", type=int, description="GPU memory used"
    )
    GPU_MEMORY_FREE: Optional[Metric] = Metric(
        name="gpu_memory_free", type=int, description="GPU memory free"
    )
    GPU_TEMPERATURE: Optional[Metric] = Metric(
        name="gpu_temperature", type=float, description="GPU temperature"
    )

    def create_gauges(self, labels: list[str]) -> dict:
        gauges = {}
        for field in fields(self):
            metric = getattr(self, field.name)
            if metric:
                if "gpu" in metric.name:
                    gauges[metric.name] = Gauge(
                        metric.name, metric.description, labelnames=labels + ["gpu_id"]
                    )
                else:
                    gauges[metric.name] = Gauge(
                        metric.name, metric.description, labelnames=labels
                    )
        return gauges


metrics = Metrics()
METRICS = metrics.create_gauges(labels=["node_id"])


def start_prometheus_exporter(port: int = 9100) -> None:
    """
    Start the Prometheus exporter to expose metrics.
    """
    logging.info("Initializing Prometheus exporter...")
    try:
        start_http_server(port)
        logging.info(f"Prometheus exporter started on port {port}")
    except Exception as e:
        logging.error(f"Failed to start Prometheus exporter: {e}")
