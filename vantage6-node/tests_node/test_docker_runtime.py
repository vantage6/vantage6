import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from vantage6.common.enum import AlgorithmStepType, RunStatus
from vantage6.common.globals import DEFAULT_ALPINE_IMAGE

from tests_node.fake_docker import FakeDockerClient
from vantage6.node.container.exceptions import PermanentAlgorithmStartFail
from vantage6.node.globals import ISOLATION_PROBE_CANDIDATES
from vantage6.node.runtime.base import (
    MountSpec,
    PullPolicy,
    RegistryCredentials,
    RunMetadata,
    RunSpec,
    RunState,
    StorageKind,
    StorageRef,
)
from vantage6.node.runtime.docker.egress import (
    HttpWhitelist,
    parse_whitelist,
    squid_config,
)
from vantage6.node.runtime.docker.runtime import (
    LABEL_NODE,
    LABEL_TYPE,
    TYPE_ALGORITHM,
    DockerRuntime,
)
from vantage6.node.runtime.docker.status import container_state

TASK = StorageRef(StorageKind.TASK)
NODE_CONTAINER = "vantage6-node-a-user-node"
HOST_TASKS = "/srv/vantage6/node-a/tasks"
CENTRAL_NET = f"{NODE_CONTAINER}-central-compute"


def make_ctx(**config) -> MagicMock:
    ctx = MagicMock()
    ctx.identifier = "abcdef0123456789"
    ctx.config = {
        "container_runtime": "docker",
        "docker": {
            "node_container": NODE_CONTAINER,
            "egress_network": f"{NODE_CONTAINER}-net",
            "task_storage": {"host_path": HOST_TASKS},
            "squid_image": "squid-image",
        },
        **config,
    }
    return ctx


def make_runtime(client=None, **config) -> DockerRuntime:
    client = client or FakeDockerClient()
    if NODE_CONTAINER not in client.containers.items:
        client.add_node_container(NODE_CONTAINER)
    return DockerRuntime(make_ctx(**config), client=client)


def make_spec(
    run_id: int = 7,
    step: AlgorithmStepType = AlgorithmStepType.FEDERATED_COMPUTE,
    pull_policy: PullPolicy = PullPolicy.ALWAYS,
    image: str = "reg.example.org/algo:1",
    mounts: list[MountSpec] | None = None,
    registries: list[RegistryCredentials] | None = None,
) -> RunSpec:
    return RunSpec(
        name=f"vantage6-run-{run_id}",
        image=image,
        step=step,
        env={"INPUT_FILE": "ENCODED"},
        secret_env={"CONTAINER_TOKEN": "secret"},
        mounts=mounts
        if mounts is not None
        else [
            MountSpec(TASK, f"{run_id}/output", "/app/vantage6/task/output"),
            MountSpec(TASK, f"{run_id}/input", "/app/vantage6/task/input", True),
            MountSpec(TASK, "sessions/session000000001", "/app/vantage6/task/session"),
        ],
        metadata=RunMetadata(
            run_id=run_id,
            task_id=100 + run_id,
            task_parent_id=None,
            init_org_id=1,
            action=step,
            session_id=1,
        ),
        pull_policy=pull_policy,
        registries=registries or [],
    )


def start(runtime: DockerRuntime, spec: RunSpec) -> tuple[RunStatus, Mock]:
    on_status_change = Mock()
    return runtime.start_run(spec, on_status_change), on_status_change


class TestEgress(unittest.TestCase):
    def test_parse(self):
        whitelists = parse_whitelist(
            {
                "data_extraction": {
                    "http": {
                        "domains": [".Example.org"],
                        "ips": ["10.0.0.1/8"],
                        "ports": [443],
                    }
                },
                "preprocessing": {"http": {}},
            }
        )
        self.assertEqual(
            whitelists,
            {
                AlgorithmStepType.DATA_EXTRACTION: HttpWhitelist(
                    (".example.org",), ("10.0.0.0/8",), (443,)
                )
            },
        )

    def test_kubernetes_rules_are_refused(self):
        with self.assertRaisesRegex(ValueError, "NetworkPolicy"):
            parse_whitelist({"data_extraction": {"egress": [{"ipBlock": {}}]}})

    def test_invalid_values_are_refused(self):
        for rules in (
            {"http": {"domains": ["example.org\nhttp_access allow all"]}},
            {"http": {"domains": ["exa mple.org"]}},
            {"http": {"ips": ["not-an-ip"]}},
            {"http": {"domains": ["example.org"], "ports": [70000]}},
            {"http": {"domains": ["example.org"], "ports": ["443"]}},
            {"other": {}},
        ):
            with self.subTest(rules), self.assertRaises(ValueError):
                parse_whitelist({"data_extraction": rules})

    def test_unknown_step_is_refused(self):
        with self.assertRaises(ValueError):
            parse_whitelist({"compute": {"http": {"domains": ["example.org"]}}})

    def test_squid_config(self):
        config = squid_config(HttpWhitelist((".example.org",), (), (443,)))
        self.assertIn("acl whitelist_domain dstdomain .example.org", config)
        self.assertIn("acl allowed_ports port 443", config)
        self.assertNotIn("whitelist_ip", config)
        self.assertTrue(
            config.index("http_access allow whitelist_domain")
            < config.index("http_access deny all")
        )


class TestContainerState(unittest.TestCase):
    def test_mapping(self):
        cases = [
            ({"Status": "created"}, (RunState.PENDING, None, None)),
            ({"Status": "running"}, (RunState.RUNNING, None, None)),
            ({"Status": "exited", "ExitCode": 0}, (RunState.SUCCEEDED, 0, None)),
            ({"Status": "exited", "ExitCode": 2}, (RunState.FAILED, 2, None)),
            (
                {"Status": "exited", "ExitCode": 137, "OOMKilled": True},
                (RunState.FAILED, 137, "OOMKilled"),
            ),
            (
                {"Status": "dead", "ExitCode": 1, "Error": "boom"},
                (RunState.FAILED, 1, "boom"),
            ),
        ]
        for state, expected in cases:
            with self.subTest(state):
                self.assertEqual(container_state({"State": state}), expected)


class TestConfiguration(unittest.TestCase):
    def test_requires_task_host_path(self):
        ctx = make_ctx()
        del ctx.config["docker"]["task_storage"]
        with self.assertRaises(ValueError):
            DockerRuntime(ctx, client=FakeDockerClient())

    def test_host_paths_come_from_the_node_container_mounts(self):
        client = FakeDockerClient()
        node = client.add_node_container(NODE_CONTAINER)
        node.attrs["Mounts"] = [
            {"Type": "bind", "Destination": "/app/tasks", "Source": "/host_mnt/tasks"},
            {
                "Type": "bind",
                "Destination": "/app/databases/db.csv",
                "Source": "/host_mnt/data/db.csv",
            },
        ]
        runtime = DockerRuntime(make_ctx(), client=client)
        self.assertEqual(runtime.task_host_path, "/host_mnt/tasks")

        start(
            runtime,
            make_spec(
                mounts=[
                    MountSpec(TASK, "7/input", "/in", True),
                    MountSpec(
                        StorageRef(StorageKind.HOST_PATH, "/Users/me/db.csv"),
                        "",
                        "/app/databases/db.csv",
                        True,
                    ),
                ]
            ),
        )
        container = client.containers.get("vantage6-run-7-abcdef01")
        self.assertEqual(
            [m["Source"] for m in container.mounts],
            ["/host_mnt/tasks/7/input", "/host_mnt/data/db.csv"],
        )

    def test_privileged_is_refused(self):
        ctx = make_ctx()
        ctx.config["docker"]["algorithm_containers"] = {"privileged": True}
        with self.assertRaises(ValueError):
            DockerRuntime(ctx, client=FakeDockerClient())

    def test_container_settings(self):
        settings = DockerRuntime._container_settings(
            {"cpus": 1.5, "memory": "2g", "pids_limit": 100, "gpus": "all"}
        )
        self.assertEqual(settings["nano_cpus"], 1_500_000_000)
        self.assertEqual(settings["mem_limit"], "2g")
        self.assertEqual(settings["pids_limit"], 100)
        self.assertEqual(settings["security_opt"], ["no-new-privileges:true"])
        self.assertEqual(settings["device_requests"][0]["Count"], -1)


class TestStartRun(unittest.TestCase):
    def test_container_gets_only_its_own_files(self):
        runtime = make_runtime()
        status, _ = start(runtime, make_spec())

        self.assertEqual(status, RunStatus.ACTIVE)
        container = runtime.client.containers.get("vantage6-run-7-abcdef01")
        self.assertEqual(
            [(m["Source"], m["Target"], m["ReadOnly"]) for m in container.mounts],
            [
                (f"{HOST_TASKS}/7/output", "/app/vantage6/task/output", False),
                (f"{HOST_TASKS}/7/input", "/app/vantage6/task/input", True),
                (
                    f"{HOST_TASKS}/sessions/session000000001",
                    "/app/vantage6/task/session",
                    False,
                ),
            ],
        )
        self.assertEqual(container.status, "running")

    def test_federated_step_has_no_network(self):
        runtime = make_runtime()
        start(runtime, make_spec())
        container = runtime.client.containers.get("vantage6-run-7-abcdef01")
        self.assertEqual(container.network_mode, "none")
        self.assertNotIn("HTTP_PROXY", container.environment)

    def test_central_step_uses_internal_network(self):
        runtime = make_runtime()
        runtime.prepare()
        start(runtime, make_spec(step=AlgorithmStepType.CENTRAL_COMPUTE))
        container = runtime.client.containers.get("vantage6-run-7-abcdef01")
        self.assertIn(CENTRAL_NET, container.attrs["NetworkSettings"]["Networks"])
        self.assertIsNone(container.network_mode)

    def test_environment_and_labels(self):
        runtime = make_runtime()
        start(runtime, make_spec())
        container = runtime.client.containers.get("vantage6-run-7-abcdef01")
        self.assertEqual(
            container.environment,
            {"INPUT_FILE": "ENCODED", "CONTAINER_TOKEN": "secret"},
        )
        self.assertEqual(container.labels[LABEL_NODE], "abcdef0123456789")
        self.assertEqual(container.labels[LABEL_TYPE], TYPE_ALGORITHM)
        self.assertNotIn("secret", str(container.labels))
        self.assertEqual(container.options["security_opt"], ["no-new-privileges:true"])

    def test_status_updates_while_pulling(self):
        runtime = make_runtime()
        _, on_status_change = start(runtime, make_spec())
        self.assertEqual(
            [c.args[0] for c in on_status_change.call_args_list],
            [RunStatus.PULLING_IMAGE, RunStatus.INITIALIZING],
        )

    def test_missing_image(self):
        runtime = make_runtime()
        runtime.client.images.missing_in_registry.add("reg.example.org/algo:1")
        status, _ = start(runtime, make_spec())
        self.assertEqual(status, RunStatus.NO_DOCKER_IMAGE)
        self.assertEqual(runtime.list_runs(), [])

    def test_if_not_present_uses_local_image(self):
        runtime = make_runtime()
        runtime.client.images.items.add("reg.example.org/algo:1")
        start(runtime, make_spec(pull_policy=PullPolicy.IF_NOT_PRESENT))
        self.assertEqual(runtime.client.images.pulls, [])

    def test_registry_credentials_are_used(self):
        runtime = make_runtime()
        registries = [
            RegistryCredentials("https://reg.example.org", "user", "pass"),
            RegistryCredentials("other.org", "x", "y"),
        ]
        start(runtime, make_spec(registries=registries))
        self.assertEqual(
            runtime.client.images.pulls,
            [("reg.example.org/algo", "1", {"username": "user", "password": "pass"})],
        )

    def test_mount_outside_task_storage_is_refused(self):
        runtime = make_runtime()
        for sub_path in ("../etc", "/etc", ".", "7/../../x"):
            spec = make_spec(mounts=[MountSpec(TASK, sub_path, "/x")])
            with self.subTest(sub_path), self.assertRaises(PermanentAlgorithmStartFail):
                start(runtime, spec)

    def test_claim_is_refused_and_host_path_is_mounted(self):
        runtime = make_runtime()
        with self.assertRaises(PermanentAlgorithmStartFail):
            start(
                runtime,
                make_spec(
                    mounts=[MountSpec(StorageRef(StorageKind.CLAIM, "pvc"), "", "/x")]
                ),
            )
        start(
            runtime,
            make_spec(
                mounts=[
                    MountSpec(
                        StorageRef(StorageKind.HOST_PATH, "/data/db.csv"),
                        "",
                        "/app/databases/db.csv",
                        True,
                    )
                ]
            ),
        )
        container = runtime.client.containers.get("vantage6-run-7-abcdef01")
        self.assertEqual(container.mounts[0]["Source"], "/data/db.csv")
        self.assertTrue(container.mounts[0]["ReadOnly"])


class TestWhitelist(unittest.TestCase):
    WHITELIST = {"data_extraction": {"http": {"domains": [".example.org"]}}}

    def test_prepare_starts_squid_on_the_step_network(self):
        client = FakeDockerClient()
        client.images.items.add("squid-image")
        runtime = make_runtime(client, whitelist=self.WHITELIST)
        client.networks.create(f"{NODE_CONTAINER}-net")
        runtime.prepare()

        squid = client.containers.get(f"{NODE_CONTAINER}-squid-data-extraction")
        self.assertEqual(squid.status, "running")
        self.assertIn(".example.org", squid.archives["/etc/squid/squid.conf"].decode())
        step_net = client.networks.get(f"{NODE_CONTAINER}-data-extraction")
        self.assertTrue(step_net.attrs["Internal"])
        self.assertEqual(step_net.members[squid.name][1], ["squid"])
        self.assertIn(
            f"{NODE_CONTAINER}-net", squid.attrs["NetworkSettings"]["Networks"]
        )
        # The node proxy is not reachable from non-central steps
        self.assertNotIn(NODE_CONTAINER, step_net.members)

    def test_whitelisted_step_gets_proxy(self):
        client = FakeDockerClient()
        runtime = make_runtime(client, whitelist=self.WHITELIST)
        client.networks.create(f"{NODE_CONTAINER}-net")
        runtime.prepare()
        start(runtime, make_spec(step=AlgorithmStepType.DATA_EXTRACTION))

        container = client.containers.get("vantage6-run-7-abcdef01")
        self.assertEqual(container.environment["HTTPS_PROXY"], "http://squid:3128")
        self.assertIn(
            f"{NODE_CONTAINER}-data-extraction",
            container.attrs["NetworkSettings"]["Networks"],
        )

    def test_whitelist_requires_egress_network(self):
        ctx = make_ctx(whitelist=self.WHITELIST)
        del ctx.config["docker"]["egress_network"]
        with self.assertRaises(ValueError):
            DockerRuntime(ctx, client=FakeDockerClient())


class TestPrepareAndCleanup(unittest.TestCase):
    def test_prepare_is_idempotent(self):
        runtime = make_runtime()
        runtime.prepare()
        runtime.prepare()
        network = runtime.client.networks.get(CENTRAL_NET)
        self.assertTrue(network.attrs["Internal"])
        self.assertIn(NODE_CONTAINER, network.members)

    def test_existing_non_internal_network_is_refused(self):
        runtime = make_runtime()
        runtime.client.networks.create(CENTRAL_NET, internal=False)
        with self.assertRaises(RuntimeError):
            runtime.prepare()

    def test_prepare_removes_containers_that_never_started(self):
        runtime = make_runtime()
        runtime.client.images.items.add("reg.example.org/algo:1")
        container = runtime.client.containers.create(
            "reg.example.org/algo:1",
            name="vantage6-run-9-abcdef01",
            labels={LABEL_NODE: "abcdef0123456789", LABEL_TYPE: TYPE_ALGORITHM},
        )
        runtime.prepare()
        self.assertTrue(container.removed)

    def test_cleanup_removes_helpers_and_networks(self):
        client = FakeDockerClient()
        client.networks.create(f"{NODE_CONTAINER}-net")
        runtime = make_runtime(
            client, whitelist={"preprocessing": {"http": {"ips": ["10.1.2.3"]}}}
        )
        runtime.prepare()
        runtime.cleanup()
        self.assertEqual(set(client.networks.items), {f"{NODE_CONTAINER}-net"})
        self.assertEqual(set(client.containers.items), {NODE_CONTAINER})


class TestListAndRecover(unittest.TestCase):
    def test_states_and_metadata(self):
        runtime = make_runtime()
        start(runtime, make_spec(run_id=1))
        start(runtime, make_spec(run_id=2))
        start(runtime, make_spec(run_id=3))
        client = runtime.client
        client.containers.get("vantage6-run-2-abcdef01").finish(0)
        client.containers.get("vantage6-run-3-abcdef01").finish(137, oom=True)

        runs = {r.metadata.run_id: r for r in runtime.list_runs()}
        self.assertEqual(runs[1].state, RunState.RUNNING)
        self.assertEqual(runs[2].state, RunState.SUCCEEDED)
        self.assertEqual(runs[3].state, RunState.FAILED)
        self.assertEqual(runs[3].reason, "OOMKilled")
        self.assertEqual(runs[1].metadata, make_spec(run_id=1).metadata)

    def test_new_runtime_finds_runs_of_previous_process(self):
        runtime = make_runtime()
        start(runtime, make_spec())
        restarted = make_runtime(runtime.client)
        self.assertTrue(restarted.run_exists("vantage6-run-7"))
        self.assertEqual([r.name for r in restarted.list_runs()], ["vantage6-run-7"])

    def test_runs_of_other_nodes_are_ignored(self):
        client = FakeDockerClient()
        runtime = make_runtime(client)
        start(runtime, make_spec())
        other_ctx = make_ctx()
        other_ctx.identifier = "ffffffff00000000"
        other = DockerRuntime(other_ctx, client=client)
        self.assertEqual(other.list_runs(), [])
        start(other, make_spec())
        self.assertEqual(len(client.containers.list(all=True)), 3)

    def test_logs_and_removal(self):
        runtime = make_runtime()
        start(runtime, make_spec())
        container = runtime.client.containers.get("vantage6-run-7-abcdef01")
        container.finish(0, b"line 1\nline 2\n")

        self.assertEqual(runtime.logs("vantage6-run-7"), "line 1\nline 2\n")
        self.assertEqual(
            list(runtime.stream_logs("vantage6-run-7")), ["line 1", "line 2"]
        )
        runtime.remove_run("vantage6-run-7", 7)
        self.assertFalse(runtime.run_exists("vantage6-run-7"))
        runtime.remove_run("vantage6-run-7", 7)


class TestChecks(unittest.TestCase):
    def test_isolation_verified(self):
        runtime = make_runtime()
        runtime.prepare()
        runtime.client.on_start = lambda c: c.finish(7)
        ok, message = runtime.verify_isolation()
        self.assertTrue(ok, message)
        self.assertEqual(
            [c for c in runtime.client.containers.items if c.startswith("v6-probe")],
            [],
        )

    def test_isolation_fails_when_a_target_is_reachable(self):
        runtime = make_runtime()
        runtime.prepare()
        target = ISOLATION_PROBE_CANDIDATES[1]
        runtime.client.on_start = lambda c: c.finish(0 if target in c.command else 7)
        ok, message = runtime.verify_isolation()
        self.assertFalse(ok)
        self.assertIn(target, message)

    def test_isolation_fails_without_internal_network(self):
        runtime = make_runtime()
        ok, _ = runtime.verify_isolation()
        self.assertFalse(ok)

    def test_preflight_reads_the_task_files_through_the_host_path(self):
        with tempfile.TemporaryDirectory() as tasks:
            client = FakeDockerClient()
            ctx = make_ctx()
            ctx.config["docker"]["task_storage"]["host_path"] = tasks
            client.add_node_container(NODE_CONTAINER)
            runtime = DockerRuntime(ctx, client=client)

            def read_marker(container):
                source = container.mounts[0]["Source"]
                marker = Path(source) / Path(container.command[-1]).name
                content = marker.read_bytes() if marker.exists() else b""
                container.finish(0 if content else 1, content)

            client.on_start = read_marker
            with patch("vantage6.node.runtime.docker.runtime.TASK_FILES_ROOT", tasks):
                ok, message = runtime.preflight()
                self.assertTrue(ok, message)
                self.assertIn(DEFAULT_ALPINE_IMAGE, client.images.items)

            with patch(
                "vantage6.node.runtime.docker.runtime.TASK_FILES_ROOT",
                str(Path(tasks) / "elsewhere"),
            ):
                (Path(tasks) / "elsewhere").mkdir()
                ok, _ = runtime.preflight()
                self.assertFalse(ok)
            self.assertEqual(list(Path(tasks).glob(".v6-*")), [])

    def test_host_reachable_url(self):
        runtime = make_runtime()
        self.assertEqual(
            runtime.host_reachable_url("http://localhost:7602/api"),
            "http://host.docker.internal:7602/api",
        )
        self.assertEqual(
            runtime.host_reachable_url("https://store.example.org"),
            "https://store.example.org",
        )


if __name__ == "__main__":
    unittest.main()
