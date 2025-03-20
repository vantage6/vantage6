import logging
from prometheus_client import Gauge, start_http_server

METRICS = {
    "cpu_percent": Gauge("cpu_percent", "CPU usage percentage", ["node_id"]),
    "memory_percent": Gauge("memory_percent", "Memory usage percentage", ["node_id"]),
    "num_algorithm_containers": Gauge(
        "num_algorithm_containers",
        "Number of running algorithm containers",
        ["node_id"],
    ),
}


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
