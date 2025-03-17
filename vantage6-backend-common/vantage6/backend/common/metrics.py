import logging
from prometheus_client import Gauge, start_http_server

NODE_CPU_PERCENT = Gauge("node_cpu_percent", "CPU usage percentage", ["node_id"])
NODE_MEMORY_PERCENT = Gauge(
    "node_memory_percent", "Memory usage percentage", ["node_id"]
)
NODE_NUM_CONTAINERS = Gauge(
    "node_num_containers", "Number of running algorithm containers", ["node_id"]
)


def start_prometheus_exporter(port: int = 9100) -> None:
    """
    Start the Prometheus exporter to expose metrics.
    """
    start_http_server(port)
    logging.info(f"Prometheus exporter started on port {port}")
