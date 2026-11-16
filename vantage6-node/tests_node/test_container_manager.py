import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from kubernetes.client.rest import ApiException

from vantage6.common.enum import AlgorithmStepType, TaskDatabaseType
from vantage6.common.globals import ContainerEnvNames, NodePolicy

from vantage6.node.container.container_manager import ContainerManager
from vantage6.node.container.exceptions import PermanentAlgorithmStartFail
from vantage6.node.container.run_io import RunIO
from vantage6.node.globals import (
    TASK_JOB_INPUT_PATH,
    TASK_JOB_OUTPUT_PATH,
    TASK_JOB_SESSION_FOLDER_PATH,
)
from vantage6.node.runtime.base import PullPolicy
from vantage6.node.runtime.kubernetes.runtime import (
    PULL_POLICIES,
    KubernetesRuntime,
    algorithm_pod_labels,
)

NODE_POD_LABELS = {"app": "node", "release": "my-node", "component": "node"}


def _k8s_runtime() -> KubernetesRuntime:
    """KubernetesRuntime configured like the Helm chart does, without a cluster."""
    runtime = KubernetesRuntime.__new__(KubernetesRuntime)
    runtime.log = _get_null_logger()
    runtime.ctx = MagicMock()
    runtime.ctx.config = {}
    runtime.task_namespace = "tenant"
    runtime.task_claim_name = "node-task-pvc"
    runtime.task_claim_sub_path = ""
    runtime.colocate_with_node = False
    runtime.node_pod_labels = NODE_POD_LABELS
    runtime.algorithm_pod_config = {}
    runtime.algorithm_pod_labels = algorithm_pod_labels("my-node")
    runtime.core_api = MagicMock()
    runtime.batch_api = MagicMock()
    runtime.task_job_labels = {"node_id": "abc"}
    runtime.task_job_label_selector = "node_id=abc"
    return runtime


def _manager(runtime=None) -> ContainerManager:
    """ContainerManager without a container platform."""
    manager = ContainerManager.__new__(ContainerManager)
    manager.log = _get_null_logger()
    manager.ctx = MagicMock()
    manager.ctx.config = {}
    manager.client = MagicMock()
    manager._policies = {}
    manager.databases = {}
    manager.share_algorithm_logs = True
    manager.runtime = runtime if runtime is not None else _k8s_runtime()
    return manager


def _run_io(action: AlgorithmStepType) -> MagicMock:
    """RunIO for run 7 in session 3 of dev node 'node_1', without touching disk."""
    run_io = MagicMock(spec=RunIO)
    run_io.action = action
    run_io.run_id = 7
    run_io.create_files.return_value = ("node_1/7/input", "node_1/7/output")
    run_io.session_file_manager = MagicMock()
    run_io.session_file_manager.session_folder = "node_1/sessions/session000000003"
    run_io.session_file_manager.session_state_file_name = "state.parquet"
    return run_io


def _get_null_logger(name="null_logger_container_manager"):
    logger = logging.getLogger(name)
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


class TestIsImageAllowed(unittest.TestCase):
    """
    Tests for ContainerManager.is_image_allowed().

    ContainerManager.__init__ talks to the Kubernetes API, so these tests bypass it
    (via __new__) and set up only the attributes is_image_allowed() actually reads:
    `_policies`, `client` and `log`. This keeps `_is_regex_pattern` (a real
    staticmethod on the class) working, unlike a fully mocked `self` would.
    """

    def setUp(self):
        self.manager = _manager()

    @staticmethod
    def _task_info(store_id: int | None = None) -> dict:
        task_info = {"init_org": {"id": 1}, "init_user": {"id": 1}}
        if store_id is not None:
            task_info["algorithm_store"] = {"id": store_id}
        return task_info

    def test_allowed_algorithms_exact_match(self):
        """Baseline regression check for the (unchanged) allowed_algorithms policy."""
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHMS.value: ["some/image:tag"]
        }

        self.assertTrue(
            self.manager.is_image_allowed("some/image:tag", self._task_info())
        )
        self.assertFalse(
            self.manager.is_image_allowed("some/other-image:tag", self._task_info())
        )

    def test_allowed_algorithm_stores_verified(self):
        """
        The store URL is whitelisted and the store itself confirms the image is a
        registered, approved algorithm there - the image is allowed.
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["https://store.example"]
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "https://store.example",
            "api_path": "/api",
        }
        self.manager.client.algorithm_store.get_algorithm.return_value = {
            "image": "some/image:tag",
            "digest": "abc123",
        }

        self.assertTrue(
            self.manager.is_image_allowed("some/image:tag", self._task_info(store_id=1))
        )
        self.manager.client.algorithm_store.get_algorithm.assert_called_once_with(
            "some/image:tag"
        )

    def test_allowed_algorithm_stores_not_confirmed_by_store(self):
        """
        The store URL is whitelisted, but the store does not confirm the image is
        registered/approved there (e.g. it genuinely isn't, the store hasn't been
        upgraded to support node requests, or it could not be reached) - the image
        is denied. This is the fix for GHSA-j43v-wwjr-9grj: previously the store URL
        match alone was enough.
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["https://store.example"]
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "https://store.example",
            "api_path": "/api",
        }
        self.manager.client.algorithm_store.get_algorithm.return_value = None

        self.assertFalse(
            self.manager.is_image_allowed("some/image:tag", self._task_info(store_id=1))
        )

    def test_allowed_algorithm_stores_url_not_whitelisted(self):
        """
        The store's URL isn't on the whitelist at all - the image is denied without
        even asking the store to verify the image (no wasted network call).
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["https://trusted.example"]
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "https://untrusted.example",
            "api_path": "/api",
        }

        self.assertFalse(
            self.manager.is_image_allowed("some/image:tag", self._task_info(store_id=1))
        )
        self.manager.client.algorithm_store.get_algorithm.assert_not_called()

    def test_allowed_algorithm_stores_localhost_translated_in_k8s(self):
        """
        A store registered under a `localhost` URL (e.g. running on the same local
        dev machine as the node) is translated to an address reachable from inside
        the node's pod before the live verification call, when V6_K8S_NODE_NAME
        indicates a local k8s dev deployment.
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["http://localhost:7601"]
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "http://localhost:7601",
            "api_path": "/api",
        }
        self.manager.client.algorithm_store.get_algorithm.return_value = {
            "image": "some/image:tag",
            "digest": "abc123",
        }

        with patch.dict(os.environ, {"V6_K8S_NODE_NAME": "docker-desktop"}):
            self.assertTrue(
                self.manager.is_image_allowed(
                    "some/image:tag", self._task_info(store_id=1)
                )
            )

        self.assertEqual(
            self.manager.client.algorithm_store.url,
            "http://host.docker.internal:7601/api",
        )

    def test_allowed_algorithm_stores_localhost_unchanged_without_k8s_node(self):
        """
        Without V6_K8S_NODE_NAME set (the default outside local dev deployments), a
        `localhost` store URL is used as-is - a real deployment never has the node
        and the store on the same machine, so there is nothing to translate.
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["http://localhost:7601"]
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "http://localhost:7601",
            "api_path": "/api",
        }
        self.manager.client.algorithm_store.get_algorithm.return_value = {
            "image": "some/image:tag",
            "digest": "abc123",
        }

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("V6_K8S_NODE_NAME", None)
            self.manager.is_image_allowed("some/image:tag", self._task_info(store_id=1))

        self.assertEqual(
            self.manager.client.algorithm_store.url, "http://localhost:7601/api"
        )

    def test_allow_either_whitelist_or_store(self):
        """
        Baseline regression check: with allow_either_whitelist_or_store, an image
        that fails the allowed_algorithms whitelist but is confirmed by the
        (whitelisted) store is still allowed.
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHMS.value: ["some/other-image:tag"],
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["https://store.example"],
            "allow_either_whitelist_or_store": True,
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "https://store.example",
            "api_path": "/api",
        }
        self.manager.client.algorithm_store.get_algorithm.return_value = {
            "image": "some/image:tag",
            "digest": "abc123",
        }

        self.assertTrue(
            self.manager.is_image_allowed("some/image:tag", self._task_info(store_id=1))
        )


class TestGetPullPolicy:
    def _manager_with_policies(self, policies: dict) -> ContainerManager:
        manager = ContainerManager.__new__(ContainerManager)
        manager._policies = policies
        return manager

    def test_require_algorithm_pull_false_means_if_not_present(self):
        manager = self._manager_with_policies({"require_algorithm_pull": False})
        assert manager._get_pull_policy() == PullPolicy.IF_NOT_PRESENT

    def test_require_algorithm_pull_true_means_always(self):
        manager = self._manager_with_policies({"require_algorithm_pull": True})
        assert manager._get_pull_policy() == PullPolicy.ALWAYS

    def test_require_algorithm_pull_absent_defaults_to_always(self):
        manager = self._manager_with_policies({})
        assert manager._get_pull_policy() == PullPolicy.ALWAYS

    def test_kubernetes_pull_policies(self):
        assert PULL_POLICIES[PullPolicy.ALWAYS] == "Always"
        assert PULL_POLICIES[PullPolicy.IF_NOT_PRESENT] == "IfNotPresent"


class TestDatabaseMountMode(unittest.TestCase):
    """
    Tests that the configured database mount mode is applied to algorithm pods
    (GHSA-27gf-8rcw-jqgh): 'ro' (default) databases are mounted read-only and file
    databases in 'copy' mode are copied, so algorithms never get write access to the
    original.
    """

    TASK_CLAIM = "node-task-pvc"
    DB_CLAIM = "hospital-data"

    def setUp(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.db_dir = Path(tmp_dir.name) / "databases"
        self.tasks_dir = Path(tmp_dir.name) / "tasks"
        self.db_dir.mkdir()
        (self.db_dir / "file_db.csv").write_text("a,b\n1,2\n")
        (self.db_dir / "dir_db.parquet").mkdir()

        for name, value in [
            ("DATABASE_BASE_PATH", str(self.db_dir)),
            ("TASK_FILES_ROOT", str(self.tasks_dir)),
        ]:
            patcher = patch(f"vantage6.node.container.container_manager.{name}", value)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.manager = _manager()

    def _get_databases(self, env: dict) -> dict:
        with patch.dict(os.environ, env, clear=True):
            return self.manager._get_database_metadata()

    @classmethod
    def _file_db_env(cls, mount_mode: str | None = None) -> dict:
        env = {
            "DATABASE_LABELS": "file_db",
            "DATABASE_FILE_DB_TYPE": "csv",
            "DATABASE_FILE_DB_CLAIM_NAME": cls.DB_CLAIM,
            "DATABASE_FILE_DB_SUB_PATH": "exports/file_db.csv",
        }
        if mount_mode is not None:
            env["DATABASE_FILE_DB_MOUNT_MODE"] = mount_mode
        return env

    def test_read_only_file_is_not_copied(self):
        db = self._get_databases(self._file_db_env("ro"))["file_db"]

        self.assertEqual(db.mount_mode, "ro")
        self.assertEqual(db.claim_name, self.DB_CLAIM)
        self.assertEqual(db.sub_path, "exports/file_db.csv")
        self.assertEqual(db.local_uri, str(self.db_dir / "file_db.csv"))
        self.assertFalse((self.tasks_dir / "databases").exists())

    def test_mount_mode_defaults_to_read_only(self):
        db = self._get_databases(self._file_db_env())["file_db"]

        self.assertEqual(db.mount_mode, "ro")
        self.assertFalse((self.tasks_dir / "databases").exists())

    def test_copy_mode_copies_file_to_task_storage(self):
        db = self._get_databases(self._file_db_env("copy"))["file_db"]

        self.assertEqual(db.mount_mode, "copy")
        self.assertIsNone(db.claim_name)
        self.assertEqual(db.sub_path, "databases/file_db.csv")
        self.assertEqual(db.local_uri, str(self.db_dir / "file_db.csv"))
        self.assertEqual(
            (self.tasks_dir / "databases" / "file_db.csv").read_text(), "a,b\n1,2\n"
        )

    def test_mount_mode_is_case_insensitive(self):
        db = self._get_databases(self._file_db_env("RO"))["file_db"]
        self.assertEqual(db.mount_mode, "ro")

    def test_copy_mode_directory_is_not_copied(self):
        env = {
            "DATABASE_LABELS": "dir_db",
            "DATABASE_DIR_DB_TYPE": "parquet",
            "DATABASE_DIR_DB_MOUNT_MODE": "copy",
            "DATABASE_DIR_DB_CLAIM_NAME": self.DB_CLAIM,
            "DATABASE_DIR_DB_SUB_PATH": "dir_db",
        }
        db = self._get_databases(env)["dir_db"]

        self.assertEqual(db.mount_mode, "copy")
        self.assertEqual(db.claim_name, self.DB_CLAIM)
        self.assertFalse((self.tasks_dir / "databases").exists())

    def test_invalid_mount_mode_raises(self):
        with self.assertRaises(ValueError):
            self._get_databases(self._file_db_env("rw"))

    def test_storage_settings_not_passed_to_algorithm_env(self):
        env = self._file_db_env("ro")
        env["DATABASE_FILE_DB_SOME_KEY"] = "some_value"
        db = self._get_databases(env)["file_db"]

        self.assertEqual(db.env, {"SOME_KEY": "some_value"})

    def _create_extraction_mounts(self, env: dict, label: str):
        self.manager.databases = self._get_databases(env)
        databases_to_use = [{"label": label, "type": TaskDatabaseType.SOURCE}]

        with patch.object(self.manager, "_validate_source_database"):
            mounts, env_vars, secrets = self.manager._create_mounts(
                _run_io(AlgorithmStepType.DATA_EXTRACTION), b"", databases_to_use
            )
        volumes, vol_mounts = self.manager.runtime.volumes_for(mounts)
        return volumes, vol_mounts, env_vars, secrets

    def _get_extraction_db_mount(self, mount_mode: str):
        volumes, vol_mounts, _, _ = self._create_extraction_mounts(
            self._file_db_env(mount_mode), "file_db"
        )
        vol_mount = next(
            m for m in vol_mounts if m.mount_path.startswith(str(self.db_dir))
        )
        volume = next(v for v in volumes if v.name == vol_mount.name)
        return volume, vol_mount

    def test_read_only_database_mounted_read_only(self):
        volume, vol_mount = self._get_extraction_db_mount("ro")

        self.assertTrue(vol_mount.read_only)
        self.assertIsNone(volume.host_path)
        self.assertEqual(volume.persistent_volume_claim.claim_name, self.DB_CLAIM)
        self.assertEqual(vol_mount.sub_path, "exports/file_db.csv")

    def test_copy_database_mounts_copy_read_write(self):
        volume, vol_mount = self._get_extraction_db_mount("copy")

        self.assertFalse(vol_mount.read_only)
        self.assertEqual(volume.persistent_volume_claim.claim_name, self.TASK_CLAIM)
        self.assertEqual(vol_mount.sub_path, "databases/file_db.csv")
        self.assertEqual(vol_mount.mount_path, str(self.db_dir / "file_db.csv"))

    def test_copy_database_is_inside_the_task_sub_path(self):
        self.manager.runtime.task_claim_sub_path = "base"
        _, vol_mount = self._get_extraction_db_mount("copy")

        self.assertEqual(vol_mount.sub_path, "base/databases/file_db.csv")

    def test_host_path_database_cannot_be_mounted_on_kubernetes(self):
        env = self._file_db_env("ro")
        del env["DATABASE_FILE_DB_CLAIM_NAME"]
        env["DATABASE_FILE_DB_HOST_PATH"] = "/data/file_db.csv"

        with self.assertRaises(PermanentAlgorithmStartFail):
            self._create_extraction_mounts(env, "file_db")

    def test_file_database_without_claim_fails_run(self):
        env = self._file_db_env("ro")
        del env["DATABASE_FILE_DB_CLAIM_NAME"]

        with self.assertRaises(PermanentAlgorithmStartFail):
            self._create_extraction_mounts(env, "file_db")

    def test_service_database_gets_no_volume(self):
        env = {
            "DATABASE_LABELS": "pg_db",
            "DATABASE_PG_DB_URI": "postgresql://host:5432/db",
            "DATABASE_PG_DB_TYPE": "sql",
        }
        volumes, _, env_vars, _ = self._create_extraction_mounts(env, "pg_db")

        self.assertEqual(
            [v.persistent_volume_claim.claim_name for v in volumes], [self.TASK_CLAIM]
        )
        self.assertEqual(
            env_vars[ContainerEnvNames.DATABASE_URI.value], "postgresql://host:5432/db"
        )


class TestRunMounts(unittest.TestCase):
    """Algorithm pods only mount the files of their own run from the task claim."""

    def _mounts(self, sub_path: str = ""):
        manager = _manager()
        manager.runtime.task_claim_sub_path = sub_path
        run_io = _run_io(AlgorithmStepType.FEDERATED_COMPUTE)
        with patch.object(manager, "_validate_dataframes"):
            mounts, _, _ = manager._create_mounts(run_io, b"", [])
        volumes, vol_mounts = manager.runtime.volumes_for(mounts)
        return volumes, {m.mount_path: m for m in vol_mounts}

    def test_single_claim_volume_without_host_paths(self):
        volumes, _ = self._mounts()

        self.assertEqual(len(volumes), 1)
        self.assertIsNone(volumes[0].host_path)
        self.assertEqual(volumes[0].persistent_volume_claim.claim_name, "node-task-pvc")

    def test_sub_paths_point_at_run_files(self):
        _, mounts = self._mounts()

        self.assertEqual(mounts[TASK_JOB_INPUT_PATH].sub_path, "node_1/7/input")
        self.assertTrue(mounts[TASK_JOB_INPUT_PATH].read_only)
        self.assertEqual(mounts[TASK_JOB_OUTPUT_PATH].sub_path, "node_1/7/output")
        self.assertFalse(mounts[TASK_JOB_OUTPUT_PATH].read_only)
        self.assertEqual(
            mounts[TASK_JOB_SESSION_FOLDER_PATH].sub_path,
            "node_1/sessions/session000000003",
        )

    def test_base_sub_path_is_prepended(self):
        _, mounts = self._mounts(sub_path="/vantage6/")

        self.assertEqual(
            mounts[TASK_JOB_INPUT_PATH].sub_path, "vantage6/node_1/7/input"
        )


class TestAlgorithmPodSpec(unittest.TestCase):
    def test_defaults(self):
        spec = _k8s_runtime().algorithm_pod_spec(containers=[])

        self.assertEqual(spec.restart_policy, "Never")
        self.assertFalse(spec.automount_service_account_token)
        self.assertIsNone(spec.affinity)
        self.assertIsNone(spec.service_account_name)

    def test_colocate_with_node_adds_pod_affinity(self):
        manager = _k8s_runtime()
        manager.colocate_with_node = True

        term = manager.algorithm_pod_spec(
            containers=[]
        ).affinity.pod_affinity.required_during_scheduling_ignored_during_execution[0]

        self.assertEqual(term.label_selector.match_labels, NODE_POD_LABELS)
        self.assertEqual(term.topology_key, "kubernetes.io/hostname")

    def test_configured_pod_settings_applied(self):
        manager = _k8s_runtime()
        resources = {"limits": {"cpu": "1", "memory": "1Gi"}}
        manager.algorithm_pod_config = {
            "resources": resources,
            "service_account_name": "anyuid",
            "runtime_class_name": "selinux",
            "pod_security_context": {"runAsNonRoot": True},
            "security_context": {"allowPrivilegeEscalation": False},
        }

        spec = manager.algorithm_pod_spec(
            containers=[manager.algorithm_container(name="c", image="i")]
        )

        self.assertEqual(spec.service_account_name, "anyuid")
        self.assertEqual(spec.runtime_class_name, "selinux")
        self.assertEqual(spec.security_context, {"runAsNonRoot": True})
        self.assertEqual(spec.containers[0].resources, resources)
        self.assertEqual(
            spec.containers[0].security_context, {"allowPrivilegeEscalation": False}
        )

    def test_algorithm_pod_labels(self):
        self.assertEqual(
            algorithm_pod_labels("my-node"),
            {"v6-pod-type": "algorithm", "v6-node-release": "my-node"},
        )
        self.assertEqual(algorithm_pod_labels(None), {"v6-pod-type": "algorithm"})


class TestKubernetesPreflight(unittest.TestCase):
    def test_test_pod_uses_algorithm_pod_settings(self):
        manager = _k8s_runtime()

        self.assertTrue(manager.preflight()[0])

        pod = manager.core_api.create_namespaced_pod.call_args.kwargs["body"]
        self.assertEqual(
            manager.core_api.create_namespaced_pod.call_args.kwargs["namespace"],
            "tenant",
        )
        self.assertEqual(pod.metadata.labels, manager.algorithm_pod_labels)
        self.assertEqual(pod.spec.restart_policy, "Never")
        manager.core_api.read_namespace.assert_not_called()
        manager.core_api.create_namespace.assert_not_called()

    def test_rejected_test_pod(self):
        manager = _k8s_runtime()
        manager.core_api.create_namespaced_pod.side_effect = ApiException(status=403)

        ok, message = manager.preflight()
        self.assertFalse(ok)
        self.assertIn("tenant", message)


if __name__ == "__main__":
    unittest.main()
