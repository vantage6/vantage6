import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from vantage6.common.enum import AlgorithmStepType, TaskDatabaseType
from vantage6.common.globals import ContainerEnvNames, NodePolicy

from vantage6.node.k8s.container_manager import ContainerManager


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
        self.manager = ContainerManager.__new__(ContainerManager)
        self.manager.log = _get_null_logger()
        self.manager.client = MagicMock()
        self.manager._policies = {}

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


class TestGetImagePullPolicy:
    def _manager_with_policies(self, policies: dict) -> ContainerManager:
        manager = ContainerManager.__new__(ContainerManager)
        manager._policies = policies
        return manager

    def test_require_algorithm_pull_false_means_if_not_present(self):
        manager = self._manager_with_policies({"require_algorithm_pull": False})
        assert manager._get_image_pull_policy() == "IfNotPresent"

    def test_require_algorithm_pull_true_means_always(self):
        manager = self._manager_with_policies({"require_algorithm_pull": True})
        assert manager._get_image_pull_policy() == "Always"

    def test_require_algorithm_pull_absent_defaults_to_always(self):
        manager = self._manager_with_policies({})
        assert manager._get_image_pull_policy() == "Always"


class TestDatabaseMountMode(unittest.TestCase):
    """
    Tests that the configured database mount mode is applied to algorithm pods
    (GHSA-27gf-8rcw-jqgh): 'ro' (default) databases are mounted read-only and file
    databases in 'copy' mode are copied, so algorithms never get write access to the
    original.
    """

    HOST_DATA_DIR = "/host/tasks"

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
            patcher = patch(f"vantage6.node.k8s.container_manager.{name}", value)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.manager = ContainerManager.__new__(ContainerManager)
        self.manager.log = _get_null_logger()
        self.manager.host_data_dir = self.HOST_DATA_DIR

    def _get_databases(self, env: dict) -> dict:
        with patch.dict(os.environ, env, clear=True):
            return self.manager._get_database_metadata()

    @staticmethod
    def _file_db_env(mount_mode: str | None = None) -> dict:
        env = {
            "DATABASE_LABELS": "file_db",
            "DATABASE_FILE_DB_URI": "/data/file_db.csv",
            "DATABASE_FILE_DB_TYPE": "csv",
        }
        if mount_mode is not None:
            env["DATABASE_FILE_DB_MOUNT_MODE"] = mount_mode
        return env

    def test_read_only_file_is_not_copied(self):
        db = self._get_databases(self._file_db_env("ro"))["file_db"]

        self.assertEqual(db.mount_mode, "ro")
        self.assertEqual(db.uri, "/data/file_db.csv")
        self.assertEqual(db.local_uri, str(self.db_dir / "file_db.csv"))
        self.assertFalse((self.tasks_dir / "databases").exists())

    def test_mount_mode_defaults_to_read_only(self):
        db = self._get_databases(self._file_db_env())["file_db"]

        self.assertEqual(db.mount_mode, "ro")
        self.assertEqual(db.uri, "/data/file_db.csv")
        self.assertFalse((self.tasks_dir / "databases").exists())

    def test_copy_mode_copies_file(self):
        db = self._get_databases(self._file_db_env("copy"))["file_db"]

        self.assertEqual(db.mount_mode, "copy")
        self.assertEqual(db.uri, f"{self.HOST_DATA_DIR}/databases/file_db.csv")
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
            "DATABASE_DIR_DB_URI": "/data/dir_db",
            "DATABASE_DIR_DB_TYPE": "parquet",
            "DATABASE_DIR_DB_MOUNT_MODE": "copy",
        }
        db = self._get_databases(env)["dir_db"]

        self.assertEqual(db.mount_mode, "copy")
        self.assertEqual(db.uri, "/data/dir_db")
        self.assertFalse((self.tasks_dir / "databases").exists())

    def test_invalid_mount_mode_raises(self):
        with self.assertRaises(ValueError):
            self._get_databases(self._file_db_env("rw"))

    def test_mount_mode_not_passed_to_algorithm_env(self):
        env = self._file_db_env("ro")
        env["DATABASE_FILE_DB_SOME_KEY"] = "some_value"
        db = self._get_databases(env)["file_db"]

        self.assertEqual(db.env, {"SOME_KEY": "some_value"})

    def _create_extraction_mounts(self, env: dict, label: str):
        self.manager.databases = self._get_databases(env)
        run_io = MagicMock()
        run_io.action = AlgorithmStepType.DATA_EXTRACTION
        run_io.run_id = 1
        run_io.create_files.return_value = ("1/input", "1/output")
        run_io.session_file_manager.session_folder = "session"
        run_io.session_file_manager.session_state_file_name = "state.parquet"
        databases_to_use = [{"label": label, "type": TaskDatabaseType.SOURCE}]

        with patch.object(self.manager, "_validate_source_database"):
            return self.manager._create_volume_mounts(run_io, b"", databases_to_use)

    def _get_extraction_db_mount(self, mount_mode: str):
        volumes, vol_mounts, _, _ = self._create_extraction_mounts(
            self._file_db_env(mount_mode), "file_db"
        )

        volume = next(v for v in volumes if v.name == "task-1-db-file_db")
        vol_mount = next(m for m in vol_mounts if m.name == "task-1-db-file_db")
        return volume, vol_mount

    def test_read_only_database_mounted_read_only(self):
        volume, vol_mount = self._get_extraction_db_mount("ro")

        self.assertTrue(vol_mount.read_only)
        self.assertEqual(volume.host_path.path, "/data/file_db.csv")

    def test_copy_database_mounts_copy_read_write(self):
        volume, vol_mount = self._get_extraction_db_mount("copy")

        self.assertFalse(vol_mount.read_only)
        self.assertEqual(
            volume.host_path.path, f"{self.HOST_DATA_DIR}/databases/file_db.csv"
        )
        self.assertEqual(vol_mount.mount_path, str(self.db_dir / "file_db.csv"))

    def test_service_database_ignores_default_read_only(self):
        env = {
            "DATABASE_LABELS": "pg_db",
            "DATABASE_PG_DB_URI": "postgresql://host:5432/db",
            "DATABASE_PG_DB_TYPE": "sql",
        }
        volumes, _, env_vars, _ = self._create_extraction_mounts(env, "pg_db")

        self.assertFalse(any(v.name == "task-1-db-pg_db" for v in volumes))
        self.assertEqual(
            env_vars[ContainerEnvNames.DATABASE_URI.value], "postgresql://host:5432/db"
        )


if __name__ == "__main__":
    unittest.main()
