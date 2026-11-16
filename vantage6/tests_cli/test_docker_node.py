import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from click.testing import CliRunner
from docker.errors import NotFound

from vantage6.cli.configuration_manager import NodeConfigurationManager
from vantage6.cli.deployment import (
    DOCKER,
    KUBERNETES,
    docker_node_context,
    get_node_deployment,
    runtime_of,
)
from vantage6.cli.deployment.docker import DockerNodeDeployment
from vantage6.cli.deployment.docker_config import (
    node_environment,
    runtime_config,
    support_image,
)
from vantage6.cli.node.common.private_key import (
    private_key_location,
    read_private_key_secret,
    write_private_key_secret,
)
from vantage6.cli.node.stop import cli_node_stop

CHARTS_DIR = Path(__file__).resolve().parents[2] / "charts"
DEPLOYMENT = "vantage6-hospital-user-node"

NODE = {
    "name": "hospital",
    "apiKey": "secret-api-key",
    "keycloak": {"url": "https://auth.example.org", "realm": "vantage6"},
    "hq": {"url": "https://hq.example.org", "port": 443, "path": "/hq"},
    "proxyPort": 7654,
    "production": True,
    "logging": {"level": "INFO"},
    "encryption": {"enabled": False},
    "databases": {
        "fileBased": [
            {"name": "patients-csv", "type": "csv", "path": "/data/patients.csv"}
        ],
        "serviceBased": [
            {
                "name": "omop",
                "type": "omop",
                "uri": "https://omop.example.org",
                "env": {"user": "reader"},
            }
        ],
    },
    "policies": {
        "allowed_algorithm_stores": ["https://store.uluru.vantage6.ai"],
        "require_algorithm_pull": True,
    },
    "private_docker_registries": [
        {"registry": "reg.example.org", "username": "u", "password": "p"}
    ],
    "algorithm_env": {"threshold": "10"},
    "whitelist": {"data_extraction": {"http": {"domains": [".example.org"]}}},
    "docker": {"algorithmContainers": {"cpus": 2, "memory": "4g"}},
}


def _ctx(tmp: Path, node: dict | None = None, encryption: bool = False) -> MagicMock:
    ctx = MagicMock()
    ctx.name = "hospital"
    ctx.deployment_name = DEPLOYMENT
    ctx.identifier = "abcdef0123456789"
    ctx.config = {"runtime": DOCKER, "node": dict(node or NODE)}
    ctx.config["node"]["encryption"] = {"enabled": encryption}
    ctx.config_dir = tmp / "config"
    ctx.data_dir = tmp / "data"
    ctx.log_dir = tmp / "log"
    ctx.is_sandbox = False
    return ctx


class TestRuntimeConfig(unittest.TestCase):
    def test_runtime_config(self):
        config = runtime_config(NODE, DEPLOYMENT, "/srv/tasks")

        self.assertEqual(config["container_runtime"], "docker")
        self.assertEqual(
            config["docker"],
            {
                "node_container": DEPLOYMENT,
                "egress_network": f"{DEPLOYMENT}-net",
                "task_storage": {"host_path": "/srv/tasks"},
                "squid_image": support_image("squid"),
                "preflight_image": support_image("alpine"),
                "algorithm_containers": {"cpus": 2, "memory": "4g"},
            },
        )
        self.assertEqual(config["whitelist"], NODE["whitelist"])
        self.assertEqual(config["network_isolation"]["verify"], True)
        self.assertNotIn("apiKey", str(config))

    def test_environment(self):
        env = node_environment(NODE, DEPLOYMENT)

        self.assertEqual(env["V6_API_KEY"], "secret-api-key")
        self.assertEqual(env["V6_PROXY_HOST"], f"http://{DEPLOYMENT}")
        self.assertEqual(env["V6_NODE_CONTAINER_NAME"], DEPLOYMENT)
        self.assertEqual(env["V6_IN_CONTAINER"], "1")
        self.assertEqual(env["DATABASE_LABELS"], "patients-csv,omop")
        self.assertEqual(env["DATABASE_PATIENTS_CSV_HOST_PATH"], "/data/patients.csv")
        self.assertEqual(env["DATABASE_PATIENTS_CSV_MOUNT_MODE"], "ro")
        self.assertEqual(env["DATABASE_OMOP_URI"], "https://omop.example.org")
        self.assertEqual(env["DATABASE_OMOP_USER"], "reader")

    @unittest.skipUnless(shutil.which("helm"), "helm is not installed")
    def test_shared_settings_match_the_helm_chart(self):
        """
        The same answers, saved as a Kubernetes or as a Docker node configuration,
        must give the node the same settings.
        """
        node = {k: v for k, v in NODE.items() if k not in ("whitelist", "docker")}
        k8s_node = dict(node)
        k8s_node["databases"] = {
            "fileBased": [
                {
                    "name": "patients-csv",
                    "type": "csv",
                    "existingClaim": "data",
                    "subPath": "patients.csv",
                }
            ],
            "serviceBased": NODE["databases"]["serviceBased"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            k8s_values = _save(Path(tmp), {"node": k8s_node})
            docker_values = _save(Path(tmp), {"runtime": DOCKER, "node": node})
            for name in ("node", "common"):
                shutil.copytree(CHARTS_DIR / name, Path(tmp) / name)
            subprocess.run(
                ["helm", "dependency", "update", f"{tmp}/node"],
                check=True,
                capture_output=True,
            )
            rendered = subprocess.run(
                ["helm", "template", "rel", f"{tmp}/node", "-f", str(k8s_values)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            docker_node = yaml.safe_load(docker_values.read_text())["node"]
        configmap = next(
            doc
            for doc in yaml.safe_load_all(rendered)
            if doc and doc["kind"] == "ConfigMap"
        )
        chart_config = yaml.safe_load(configmap["data"]["config.yml"])
        docker_config = runtime_config(docker_node, DEPLOYMENT, "/srv/tasks")

        shared = (
            "hq_url",
            "api_path",
            "port",
            "node_proxy_port",
            "production",
            "share_config",
            "share_algorithm_logs",
            "allow_http_polling",
            "encryption",
            "policies",
            "prometheus",
            "private_docker_registries",
        )
        for key in shared:
            with self.subTest(key):
                self.assertEqual(docker_config.get(key), chart_config.get(key))
        for key in ("level", "file", "max_size", "backup_count", "format", "datefmt"):
            with self.subTest(f"logging.{key}"):
                self.assertEqual(
                    docker_config["logging"][key], chart_config["logging"][key]
                )
        # The chart writes values unquoted, so YAML may turn them into numbers
        self.assertEqual(
            {k: str(v) for k, v in docker_config["algorithm_env"].items()},
            {k: str(v) for k, v in chart_config["algorithm_env"].items()},
        )


def _save(folder: Path, config: dict) -> Path:
    manager = NodeConfigurationManager("hospital")
    manager.put(config)
    path = folder / f"{config.get('runtime', 'kubernetes')}.yaml"
    manager.save(path)
    return path


class TestTemplate(unittest.TestCase):
    def test_docker_values_render_to_the_docker_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = NodeConfigurationManager("hospital")
            manager.put({"runtime": DOCKER, "node": NODE})
            path = Path(tmp) / "hospital.yaml"
            manager.save(path)
            saved = yaml.safe_load(path.read_text())

        self.assertEqual(saved["runtime"], DOCKER)
        self.assertNotIn("persistence", saved["node"])
        self.assertNotIn("networkPolicy", saved["node"])
        file_db = saved["node"]["databases"]["fileBased"][0]
        self.assertEqual(file_db["path"], "/data/patients.csv")
        self.assertEqual(file_db["mount_mode"], "ro")
        self.assertEqual(
            saved["node"]["databases"]["serviceBased"],
            NODE["databases"]["serviceBased"],
        )
        self.assertEqual(saved["node"]["whitelist"], NODE["whitelist"])
        self.assertEqual(
            saved["node"]["docker"]["algorithmContainers"], {"cpus": 2, "memory": "4g"}
        )
        # The saved file can be turned into a runtime configuration
        runtime_config(saved["node"], DEPLOYMENT, "/srv/tasks")

    def test_kubernetes_values_still_render_to_the_helm_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = NodeConfigurationManager("hospital")
            manager.put(
                {
                    "node": {
                        "name": "n",
                        "apiKey": "k",
                        "hq": {"url": "x"},
                        "keycloak": {"url": "y"},
                        "logging": {},
                    }
                }
            )
            path = Path(tmp) / "n.yaml"
            manager.save(path)
            saved = yaml.safe_load(path.read_text())
        self.assertNotIn("runtime", saved)
        self.assertIn("persistence", saved["node"])


class TestRuntimeSelection(unittest.TestCase):
    def test_runtime_of(self):
        ctx = MagicMock(config={})
        self.assertEqual(runtime_of(ctx), KUBERNETES)
        ctx.config = {"runtime": DOCKER}
        self.assertEqual(runtime_of(ctx), DOCKER)
        ctx.config = {"runtime": "podman"}
        with self.assertRaises(ValueError):
            runtime_of(ctx)

    def test_docker_node_needs_no_kubernetes(self):
        ctx = MagicMock(config={"runtime": DOCKER, "node": NODE})
        with patch("vantage6.cli.deployment.kubernetes.select_k8s_config") as select:
            deployment = get_node_deployment(ctx, context="c", namespace="n")
        self.assertIsInstance(deployment, DockerNodeDeployment)
        select.assert_not_called()

    def test_docker_node_context(self):
        with (
            patch("vantage6.cli.context.node.NodeContext.config_exists") as exists,
            patch("vantage6.cli.context.get_context") as get_context,
        ):
            exists.return_value = False
            self.assertIsNone(docker_node_context("x", False, False))
            exists.return_value = True
            get_context.return_value = MagicMock(config={"runtime": DOCKER})
            self.assertIs(
                docker_node_context("x", False, False), get_context.return_value
            )
            get_context.return_value = MagicMock(config={})
            self.assertIsNone(docker_node_context("x", False, False))


class TestDockerNodeDeployment(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.client = MagicMock()
        self.client.api.base_url = "http+docker://localhost"
        self.client.info.return_value = {"OperatingSystem": "Docker Desktop"}
        self.client.containers.get.side_effect = NotFound("no node")
        self.client.networks.list.return_value = []

    def _deployment(self, **kwargs) -> DockerNodeDeployment:
        node = dict(NODE)
        db = self.tmp / "patients.csv"
        db.write_text("a\n1\n")
        node["databases"] = {
            "fileBased": [
                {"name": "patients-csv", "type": "csv", "path": str(db)},
            ],
            "serviceBased": [],
        }
        node["image"] = "node-image"
        return DockerNodeDeployment(_ctx(self.tmp, node, **kwargs), client=self.client)

    def test_start(self):
        deployment = self._deployment()
        deployment.start("node-image")

        self.client.images.pull.assert_called_once_with("node-image")
        self.client.networks.create.assert_called_once()
        kwargs = self.client.containers.run.call_args.kwargs
        self.assertEqual(kwargs["name"], DEPLOYMENT)
        self.assertEqual(kwargs["network"], f"{DEPLOYMENT}-net")
        self.assertEqual(kwargs["restart_policy"], {"Name": "unless-stopped"})
        self.assertEqual(
            kwargs["command"], ["vnode-local", "start", "-c", "/app/config/config.yml"]
        )
        mounts = {m["Target"]: m for m in kwargs["mounts"]}
        self.assertEqual(
            mounts["/var/run/docker.sock"]["Source"], "/var/run/docker.sock"
        )
        self.assertEqual(
            mounts["/app/tasks"]["Source"], str((self.tmp / "data/tasks").resolve())
        )
        self.assertTrue(mounts["/app/databases/patients-csv.csv"]["ReadOnly"])
        self.assertTrue(mounts["/app/config/config.yml"]["ReadOnly"])
        self.assertNotIn("/app/encryption/private_key.pem", mounts)

        config_file = self.tmp / "data/runtime/config.yml"
        self.assertEqual(oct(config_file.stat().st_mode & 0o777), "0o600")
        config = yaml.safe_load(config_file.read_text())
        self.assertEqual(config["docker"]["node_container"], DEPLOYMENT)
        self.assertNotIn("user", kwargs)

    def test_native_linux_runs_as_current_user(self):
        deployment = self._deployment()
        self.client.info.return_value = {"OperatingSystem": "Ubuntu 24.04"}
        self.client.api.base_url = "http+docker://localunixsocket"
        socket = self.tmp / "docker.sock"
        socket.touch()
        with (
            patch(
                "vantage6.cli.deployment.docker.platform.system", return_value="Linux"
            ),
            patch.dict(deployment.docker_cfg, {"socketPath": str(socket)}),
        ):
            deployment.start("node-image")
        kwargs = self.client.containers.run.call_args.kwargs
        self.assertEqual(kwargs["user"], f"{os.getuid()}:{os.getgid()}")
        self.assertEqual(kwargs["group_add"], [str(socket.stat().st_gid)])

    def test_encrypted_node_needs_its_key(self):
        deployment = self._deployment(encryption=True)
        with self.assertRaises(SystemExit):
            deployment.start("node-image")
        self.client.containers.run.assert_not_called()

        deployment.write_private_key(b"pem")
        self.assertEqual(
            oct(deployment.private_key_file.stat().st_mode & 0o777), "0o600"
        )
        deployment.start("node-image")
        mounts = {
            m["Target"]: m
            for m in self.client.containers.run.call_args.kwargs["mounts"]
        }
        self.assertTrue(mounts["/app/encryption/private_key.pem"]["ReadOnly"])

    def test_already_running(self):
        deployment = self._deployment()
        self.client.containers.get.side_effect = None
        self.client.containers.get.return_value.status = "running"
        with self.assertRaises(SystemExit):
            deployment.start("node-image")

    def test_stop_removes_everything_of_the_node(self):
        deployment = self._deployment()
        node_container = MagicMock()
        self.client.containers.get.side_effect = None
        self.client.containers.get.return_value = node_container
        algorithm = MagicMock()
        network = MagicMock()
        self.client.containers.list.return_value = [algorithm]
        self.client.networks.list.return_value = [network]

        deployment.stop()

        node_container.stop.assert_called_once()
        algorithm.remove.assert_called_once_with(force=True)
        network.remove.assert_called_once()
        self.assertEqual(
            self.client.containers.list.call_args.kwargs["filters"],
            {"label": ["vantage6.node_id=abcdef0123456789"]},
        )


class TestPrivateKeyFile(unittest.TestCase):
    def test_docker_node_keeps_its_key_in_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = _ctx(Path(tmp))
            with patch(
                "vantage6.cli.node.common.private_key.get_core_api_with_ssl_handling"
            ) as core_api:
                self.assertIsNone(read_private_key_secret(ctx, None))
                write_private_key_secret(ctx, None, b"pem")
                self.assertEqual(read_private_key_secret(ctx, None), b"pem")
            core_api.assert_not_called()
            self.assertIn("private_key.pem", private_key_location(ctx))


class TestStopCommand(unittest.TestCase):
    @patch("vantage6.cli.node.stop.execute_stop")
    @patch("vantage6.cli.node.stop.DockerNodeDeployment")
    @patch("vantage6.cli.node.stop.docker_node_context")
    def test_named_docker_node(self, docker_ctx, deployment, execute_stop):
        result = CliRunner().invoke(cli_node_stop, ["--name", "hospital"])
        self.assertEqual(result.exit_code, 0, result.output)
        deployment.return_value.stop.assert_called_once()
        execute_stop.assert_not_called()

    @patch("vantage6.cli.node.stop.execute_stop")
    @patch("vantage6.cli.node.stop.DockerNodeDeployment")
    @patch("vantage6.cli.node.stop.node_config_runtimes", return_value={DOCKER})
    @patch("vantage6.cli.node.stop.running_docker_node_contexts")
    def test_all_docker_nodes_without_kubernetes(
        self, running, _runtimes, deployment, execute_stop
    ):
        running.return_value = [MagicMock(), MagicMock()]
        result = CliRunner().invoke(cli_node_stop, ["--all"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(deployment.return_value.stop.call_count, 2)
        execute_stop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
