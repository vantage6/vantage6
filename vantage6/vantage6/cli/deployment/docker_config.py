"""
Turn a node configuration file (the ``node:`` values) into what a Docker node
container needs: the runtime configuration file and its environment. On Kubernetes,
the node Helm chart does the same (``node-configmap.yml``, ``node-secrets.yml`` and
``node-deployment.yml``).
"""

from pathlib import PurePosixPath

from vantage6.common.enum import DatabaseMountMode
from vantage6.common.globals import DEFAULT_DOCKER_REGISTRY
from vantage6.common.kubernetes.utils import database_env_label

from vantage6.cli import __version__

DATABASE_BASE_PATH = PurePosixPath("/app/databases")
NODE_CONFIG_PATH = "/app/config/config.yml"
PRIVATE_KEY_PATH = "/app/encryption/private_key.pem"
TASK_FILES_ROOT = "/app/tasks"
LOG_DIR = "/mnt/log"
DATA_DIR = "/mnt/data"
DOCKER_SOCKET = "/var/run/docker.sock"

DEFAULT_LOGGERS = [
    {"level": "warning", "name": name}
    for name in (
        "urllib3",
        "socketIO-client",
        "socketio.server",
        "engineio.server",
        "docker.utils.config",
    )
]


def support_image(name: str, version: str = __version__) -> str:
    """Support image published with this vantage6 version, as the charts use."""
    return f"{DEFAULT_DOCKER_REGISTRY}/infrastructure/{name}:{version.replace('-', '')}"


def egress_network(deployment_name: str) -> str:
    return f"{deployment_name}-net"


def file_databases(node: dict) -> list[dict]:
    return (node.get("databases") or {}).get("fileBased") or []


def service_databases(node: dict) -> list[dict]:
    return (node.get("databases") or {}).get("serviceBased") or []


def database_mount_path(db: dict) -> str:
    return str(DATABASE_BASE_PATH / f"{db['name']}.{db['type']}")


def runtime_config(node: dict, deployment_name: str, task_host_path: str) -> dict:
    """Configuration file read by ``vnode-local start`` in the node container."""
    hq = node.get("hq") or {}
    docker = node.get("docker") or {}
    isolation = docker.get("networkIsolation") or {}
    logging = node.get("logging") or {}
    policies = node.get("policies") or {}
    prometheus = node.get("prometheus") or {}

    config = {
        "container_runtime": "docker",
        "hq_url": hq.get("url"),
        "api_path": hq.get("path", "/hq"),
        "port": hq.get("port", 7601),
        "node_proxy_port": node.get("proxyPort", 7654),
        "docker": {
            "node_container": deployment_name,
            "egress_network": egress_network(deployment_name),
            "task_storage": {"host_path": task_host_path},
            "squid_image": docker.get("squidImage") or support_image("squid"),
            "preflight_image": docker.get("preflightImage") or support_image("alpine"),
            "algorithm_containers": docker.get("algorithmContainers") or {},
        },
        "network_isolation": {
            "verify": isolation.get("verify", True),
            "probe_image": isolation.get("probeImage") or support_image("curl"),
        },
        "production": node.get("production", True),
        "share_config": node.get("share_config", True),
        "share_algorithm_logs": node.get("share_algorithm_logs", True),
        "allow_http_polling": node.get("allow_http_polling", False),
        "encryption": {"enabled": (node.get("encryption") or {}).get("enabled", False)},
        "logging": {
            "backup_count": logging.get("backup_count", 5),
            "datefmt": logging.get("datefmt", "%Y-%m-%d %H:%M:%S"),
            "file": logging.get("file", "node.log"),
            "format": logging.get(
                "format",
                "%(asctime)s - %(name)-14s - %(levelname)-8s - %(message)s",
            ),
            "level": logging.get("level", "INFO"),
            "max_size": logging.get("max_size", 1024),
            "use_console": logging.get("use_console", True),
            "loggers": logging.get("loggers") or DEFAULT_LOGGERS,
        },
        "policies": {
            **{
                key: policies[key]
                for key in (
                    "allowed_algorithms",
                    "allowed_algorithm_stores",
                    "allowed_users",
                    "allowed_organizations",
                )
                if policies.get(key)
            },
            "require_algorithm_pull": policies.get("require_algorithm_pull", True),
            "allow_either_whitelist_or_store": policies.get(
                "allow_either_whitelist_or_store", False
            ),
        },
        "prometheus": {"enabled": prometheus.get("enabled", False)},
    }
    if config["prometheus"]["enabled"]:
        config["prometheus"]["report_interval_seconds"] = prometheus.get(
            "report_interval_seconds", 60
        )
    for key in ("private_docker_registries", "algorithm_env", "whitelist", "debug"):
        if node.get(key):
            config[key] = node[key]
    if (node.get("dev") or {}).get("task_dir_extension"):
        config["dev"] = {"task_dir_extension": node["dev"]["task_dir_extension"]}
    return config


def node_environment(node: dict, deployment_name: str) -> dict[str, str]:
    """Environment of the node container."""
    keycloak = node.get("keycloak") or {}
    env = {
        "V6_API_KEY": node["apiKey"],
        "V6_NODE_NAME": node["name"],
        "KEYCLOAK_URL": keycloak.get("url", ""),
        "KEYCLOAK_REALM": keycloak.get("realm", "vantage6"),
        "V6_PROXY_PORT": str(node.get("proxyPort", 7654)),
        "V6_PROXY_HOST": f"http://{deployment_name}",
        "V6_IN_CONTAINER": "1",
        "V6_NODE_CONTAINER_NAME": deployment_name,
    }
    databases = file_databases(node) + service_databases(node)
    env["DATABASE_LABELS"] = ",".join(db["name"] for db in databases)
    for db in databases:
        label = database_env_label(db["name"])
        env[f"DATABASE_{label}_URI"] = db.get("uri") or ""
        env[f"DATABASE_{label}_TYPE"] = db["type"]
        for key, value in (db.get("env") or {}).items():
            env[f"DATABASE_{label}_{key.upper()}"] = str(value)
    for db in file_databases(node):
        label = database_env_label(db["name"])
        env[f"DATABASE_{label}_MOUNT_MODE"] = db.get("mount_mode") or "ro"
        env[f"DATABASE_{label}_HOST_PATH"] = db["path"]
    return env


def database_read_only(db: dict) -> bool:
    return (db.get("mount_mode") or "ro") == DatabaseMountMode.READ_ONLY.value
