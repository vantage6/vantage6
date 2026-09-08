"""Tests for the local-filesystem large-result-store backend."""

import io
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from vantage6.common.globals import DEFAULT_CHUNK_SIZE
from vantage6.server.service.file_storage_service import (
    DEFAULT_RUN_DATA_BASE_PATH,
    RUN_DATA_BASE_PATH_ENV_VAR,
    FileStorageService,
)
from sqlalchemy import inspect

from vantage6.server.model.run import Run
from vantage6.server.service.storage_adapter import (
    RunDataDeletionError,
    RunDataNotFoundError,
    _dispatch_run_data_delete_after_run_delete,
    build_storage_adapter,
)


def _uuid() -> str:
    return str(uuid.uuid4())


class _StubRun:
    """Stands in for a Run row when exercising the after_delete listener."""

    def __init__(self, result: str | None, input: str | None, id: int = 1) -> None:
        self.blob_storage_used = True
        self.result = result
        self.input = input
        self.id = id


class TestFileStorageService(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)
        self.adapter = FileStorageService({}, base_path=self.tmp_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_bytes_roundtrip(self) -> None:
        name = _uuid()
        payload = b"hello world"
        self.adapter.store_run_data(name, payload)
        self.assertEqual(self.adapter.get_run_data(name), payload)

    def test_stream_roundtrip(self) -> None:
        name = _uuid()
        # Span several read chunks with a non-aligned tail to exercise partial reads.
        payload = b"x" * (3 * DEFAULT_CHUNK_SIZE + 17)
        self.adapter.store_run_data(name, payload)

        chunks = list(self.adapter.stream_run_data(name).chunks())
        self.assertEqual(b"".join(chunks), payload)
        self.assertTrue(all(c for c in chunks))

    def test_iostream_roundtrip(self) -> None:
        name = _uuid()
        # Span several write chunks with a non-aligned tail to exercise partial writes.
        payload = os.urandom(3 * DEFAULT_CHUNK_SIZE + 17)
        self.adapter.store_run_data(name, io.BytesIO(payload))
        self.assertEqual(self.adapter.get_run_data(name), payload)

    def test_sharded_layout(self) -> None:
        name = _uuid()
        self.adapter.store_run_data(name, b"x")
        self.assertTrue((self.tmp_path / name[:2] / name).is_file())

    def test_delete_idempotent(self) -> None:
        name = _uuid()
        self.adapter.delete_run_data(name)  # missing — should not raise
        self.adapter.store_run_data(name, b"x")
        self.adapter.delete_run_data(name)
        self.assertFalse((self.adapter.base_path / name[:2] / name).exists())
        self.adapter.delete_run_data(name)  # idempotent after delete

    def test_atomic_write_crash_safety(self) -> None:
        name = _uuid()
        with patch(
            "vantage6.server.service.file_storage_service.os.replace",
            side_effect=OSError("simulated crash"),
        ):
            with self.assertRaises(RuntimeError):
                self.adapter.store_run_data(name, b"payload")

        shard = self.adapter.base_path / name[:2]
        target = shard / name
        self.assertFalse(target.exists())
        if shard.exists():
            self.assertFalse(any(p.name.startswith(".tmp-") for p in shard.iterdir()))

    def test_path_traversal_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.store_run_data("../etc/passwd", b"x")
        with self.assertRaises(ValueError):
            self.adapter.store_run_data("a/b", b"x")
        with self.assertRaises(ValueError):
            self.adapter.get_run_data("")

    def test_trailing_newline_rejected(self) -> None:
        """``$`` also matches before a trailing newline, so the name pattern
        must be applied with ``fullmatch`` — otherwise ``"ab\\n"`` passes
        validation and lands on disk as a filename ending in a newline.
        """
        with self.assertRaises(ValueError):
            self.adapter.store_run_data("ab\n", b"x")
        with self.assertRaises(ValueError):
            self.adapter.get_run_data(f"{_uuid()}\n")

    def test_base_path_resolved(self) -> None:
        adapter = FileStorageService({}, base_path=self.tmp_path)
        self.assertEqual(adapter.base_path, self.tmp_path.resolve())

    @unittest.skipUnless(
        os.name == "posix" and os.geteuid() != 0,
        "needs POSIX permissions and a non-root user (root bypasses mode bits)",
    )
    def test_unwritable_base_path_fails_at_startup(self) -> None:
        """A read-only storage root (unmounted or misconfigured volume)
        must fail when the adapter is built, not as a 500 on first upload."""
        read_only = self.tmp_path / "read-only-root"
        read_only.mkdir(mode=0o500)
        try:
            with self.assertRaises(RuntimeError):
                FileStorageService({}, base_path=read_only)
        finally:
            read_only.chmod(0o700)

    def test_stream_missing_run_data_raises(self) -> None:
        with self.assertRaises(RunDataNotFoundError):
            self.adapter.stream_run_data(_uuid())

    def test_get_missing_run_data_raises(self) -> None:
        with self.assertRaises(RunDataNotFoundError):
            self.adapter.get_run_data(_uuid())

    @unittest.skipUnless(os.name == "posix", "relies on POSIX unlink semantics")
    def test_stream_survives_delete_after_open(self) -> None:
        """A delete racing an in-flight read must not truncate the response.

        ``stream_run_data`` opens the entry before returning, so the reader
        holds a live handle. Removing the directory entry afterwards leaves
        the inode readable, which is what stops a partial body being sent
        under an already-committed 200.
        """
        name = _uuid()
        payload = b"payload that outlives its directory entry"
        self.adapter.store_run_data(name, payload)

        stream = self.adapter.stream_run_data(name)
        self.adapter.delete_run_data(name)
        self.assertFalse((self.adapter.base_path / name[:2] / name).exists())

        self.assertEqual(b"".join(stream.chunks()), payload)

    def test_stream_can_be_closed_without_reading(self) -> None:
        name = _uuid()
        self.adapter.store_run_data(name, b"x")

        self.adapter.stream_run_data(name).close()

        with self.adapter.stream_run_data(name) as stream:
            self.assertEqual(b"".join(stream.chunks()), b"x")

    def test_delete_retains_shard_directory(self) -> None:
        """Shards are never pruned, so a delete cannot race a concurrent store."""
        name = _uuid()
        self.adapter.store_run_data(name, b"x")
        shard = self.adapter.base_path / name[:2]

        self.adapter.delete_run_data(name)

        self.assertTrue(shard.is_dir())

    def test_store_after_delete_in_same_shard(self) -> None:
        first, second = "aa-first-entry", "aa-second-entry"
        self.adapter.store_run_data(first, b"1")
        self.adapter.delete_run_data(first)

        self.adapter.store_run_data(second, b"2")

        self.assertEqual(self.adapter.get_run_data(second), b"2")


class TestRunDataCascadeDeletion(unittest.TestCase):
    """Tests for the shared after_delete listener defined on StorageAdapter.

    The listener is invoked directly rather than through a SQLAlchemy flush,
    so these stay unit tests: what matters is which entries it removes and
    how it reports failure, not the event plumbing.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.adapter = FileStorageService({}, base_path=Path(self._tmp.name))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_skips_runs_not_using_the_store(self) -> None:
        target = _StubRun(result="aa-result", input="aa-input")
        target.blob_storage_used = False

        with patch.object(self.adapter, "delete_run_data") as delete:
            self.adapter._delete_run_data_after_run_delete(None, None, target)

        delete.assert_not_called()

    def test_deletes_both_input_and_result(self) -> None:
        target = _StubRun(result="aa-result", input="aa-input")

        with patch.object(self.adapter, "delete_run_data") as delete:
            self.adapter._delete_run_data_after_run_delete(None, None, target)

        self.assertEqual(
            [call.args[0] for call in delete.call_args_list],
            ["aa-result", "aa-input"],
        )

    def test_repeated_construction_registers_one_listener(self) -> None:
        """The cascade must not grow as adapters are constructed.

        ``event.listen`` targets the mapped ``Run`` class, which outlives
        any single adapter, so a listener registered per instance would
        never be released.
        """
        after_first = len(inspect(Run).dispatch.after_delete)

        for _ in range(5):
            FileStorageService({}, base_path=Path(self._tmp.name))

        self.assertEqual(len(inspect(Run).dispatch.after_delete), after_first)

    def test_cascade_dispatches_to_most_recent_adapter(self) -> None:
        latest = FileStorageService({}, base_path=Path(self._tmp.name))
        target = _StubRun(result="aa-result", input=None)

        with patch.object(self.adapter, "delete_run_data") as stale:
            with patch.object(latest, "delete_run_data") as active:
                _dispatch_run_data_delete_after_run_delete(None, None, target)

        stale.assert_not_called()
        active.assert_called_once_with("aa-result")

    def test_failure_attempts_both_and_reports_both(self) -> None:
        target = _StubRun(result="aa-result", input="aa-input")

        with patch.object(
            self.adapter, "delete_run_data", side_effect=OSError("mount gone")
        ) as delete:
            with self.assertRaises(RunDataDeletionError) as ctx:
                self.adapter._delete_run_data_after_run_delete(None, None, target)

        self.assertEqual(delete.call_count, 2)
        self.assertIn("aa-result", str(ctx.exception))
        self.assertIn("aa-input", str(ctx.exception))
        self.assertIsInstance(ctx.exception.__cause__, OSError)


class TestStorageAdapterFactory(unittest.TestCase):
    def test_factory_returns_none_when_unset(self) -> None:
        self.assertIsNone(build_storage_adapter({}))

    def test_factory_uses_env_var_for_base_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {RUN_DATA_BASE_PATH_ENV_VAR: tmp}):
                adapter = build_storage_adapter({"large_run_data_store": "filesystem"})
            self.assertIsInstance(adapter, FileStorageService)
            self.assertEqual(adapter.base_path, Path(tmp).resolve())

    def test_factory_falls_back_to_default_when_env_unset(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != RUN_DATA_BASE_PATH_ENV_VAR}
        with patch.dict(os.environ, env, clear=True):
            with patch(
                "vantage6.server.service.file_storage_service.Path.mkdir"
            ) as mock_mkdir:
                # The default path does not exist on the test host; the
                # writability gate is exercised by its own test above.
                with patch(
                    "vantage6.server.service.file_storage_service.os.access",
                    return_value=True,
                ):
                    adapter = build_storage_adapter(
                        {"large_run_data_store": "filesystem"}
                    )
        self.assertIsInstance(adapter, FileStorageService)
        self.assertEqual(adapter.base_path, Path(DEFAULT_RUN_DATA_BASE_PATH).resolve())
        mock_mkdir.assert_called()

    def test_factory_rejects_deprecated_large_result_store_key(self) -> None:
        with self.assertRaises(ValueError) as cm:
            build_storage_adapter({"large_result_store": {"type": "file"}})
        self.assertIn("large_result_store", str(cm.exception))

    def test_factory_rejects_unknown_store_type(self) -> None:
        with self.assertRaises(ValueError):
            build_storage_adapter({"large_run_data_store": "s3"})

    def test_factory_rejects_azure_without_block(self) -> None:
        with self.assertRaises(ValueError) as cm:
            build_storage_adapter({"large_run_data_store": "azure"})
        self.assertIn("azure_run_data_store", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
