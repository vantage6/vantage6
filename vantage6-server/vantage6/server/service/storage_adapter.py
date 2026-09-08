"""Abstract storage adapter for the large result store.

Provides a backend-agnostic interface for storing run inputs and results
(``store_run_data`` / ``get_run_data`` / ``stream_run_data`` /
``delete_run_data``) along with a shared SQLAlchemy ``after_delete``
listener on :class:`Run` that removes the associated run data whenever
a Run row is deleted.

Concrete backends (Azure Blob Storage, local filesystem) subclass
:class:`StorageAdapter` and call ``super().__init__(config)`` only after
they are fully usable, so the listener is never registered against a
half-initialised adapter.

The module also exposes :func:`build_storage_adapter`, a small factory
that dispatches on the top-level ``large_run_data_store`` setting (a
string: ``"filesystem"`` or ``"azure"``). When ``"azure"`` is selected,
the Azure-specific block lives under ``azure_run_data_store``.
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import IO, Iterator, Union

from sqlalchemy import event

from vantage6.common import logger_name
from vantage6.server.model.run import Run

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class RunDataNotFoundError(Exception):
    """Raised by storage adapters when no entry exists for the given name.

    Backend-neutral: file backend raises this in place of the bare
    ``FileNotFoundError`` from ``Path.read_bytes()``; Azure backend
    raises it in place of ``azure.core.exceptions.ResourceNotFoundError``.
    """


class RunDataDeletionError(RuntimeError):
    """Raised when run data could not be removed after its Run row was deleted.

    This comes from the ``after_delete`` listener, so raising it aborts the
    surrounding flush and the Run row is not deleted either. That is
    deliberate. Orphaned inputs and results left on a storage backend are a
    data-protection problem, so the delete fails closed rather than
    succeeding and leaking; an operator can retry once the backend is
    reachable again.

    The distinct type and the message exist so that a storage-layer failure
    is not mistaken for a database one, which is how the previous bare
    ``RuntimeError`` presented. Subclassing ``RuntimeError`` keeps callers
    that already catch the old behaviour working.
    """


class RunDataStream(ABC):
    """Streaming reader for stored run data.

    The shape mirrors Azure SDK's ``StorageStreamDownloader.chunks()`` so
    the existing call site in ``blobstream.py`` works unchanged for both
    backends.
    """

    @abstractmethod
    def chunks(self) -> Iterator[bytes]:
        """Yield successive chunks of the run data's content."""


def _dispatch_run_data_delete_after_run_delete(mapper, connection, target) -> None:
    """
    Forward a ``Run`` deletion to the active storage adapter.

    Registered against the ``Run`` class exactly once, however many
    adapters are constructed. When no adapter is active there is no
    stored run data to clean up and this is a no-op.
    """
    adapter = StorageAdapter._active
    if adapter is not None:
        adapter._delete_run_data_after_run_delete(mapper, connection, target)


class StorageAdapter(ABC):
    """Abstract base class for large-result storage backends.

    At most one adapter per process is wired into the ``Run`` delete
    cascade. ``_active`` holds that adapter and ``_listener_registered``
    records whether the class-level listener has been attached:
    ``event.listen`` targets the mapped ``Run`` class, which lives for the
    whole process and never releases what is registered against it, so a
    listener per adapter instance would accumulate for as long as the
    process keeps constructing adapters — and every one of them would fire
    on every ``Run`` deletion. Constructing another adapter therefore
    replaces the dispatch target rather than adding a listener.
    """

    _active: "StorageAdapter | None" = None
    _listener_registered: bool = False

    def __init__(self, config: dict) -> None:
        StorageAdapter._active = self
        if not StorageAdapter._listener_registered:
            event.listen(
                Run, "after_delete", _dispatch_run_data_delete_after_run_delete
            )
            StorageAdapter._listener_registered = True

    @abstractmethod
    def get_run_data(self, name: str) -> bytes:
        """Return the full content of a run-data entry as bytes.

        Raises
        ------
        RunDataNotFoundError
            If no entry exists for ``name``.
        """

    @abstractmethod
    def store_run_data(self, name: str, data: Union[IO, bytes]) -> None:
        """Store data under the given run-data name."""

    @abstractmethod
    def delete_run_data(self, name: str) -> None:
        """Delete a run-data entry. Must be idempotent (no error if missing)."""

    @abstractmethod
    def stream_run_data(self, name: str):
        """Return a streaming reader exposing a ``chunks()`` iterator.

        Raises
        ------
        RunDataNotFoundError
            If no entry exists for ``name``.
        """

    def _delete_run_data_after_run_delete(self, mapper, connection, target) -> None:
        """Remove the associated run data when a Run row is deleted.

        Both the input and the result are attempted even if the first fails,
        so a single unreadable entry does not hide the state of the other.
        Any failure raises :class:`RunDataDeletionError`, which aborts the
        flush and leaves the Run row in place rather than orphaning stored
        data.
        """
        if not getattr(target, "blob_storage_used", False):
            return

        failures = []
        for name in (target.result, target.input):
            if not name:
                continue
            try:
                self.delete_run_data(name)
            except Exception as e:
                failures.append((name, e))

        if failures:
            detail = "; ".join(f"{name!r}: {e}" for name, e in failures)
            error_msg = (
                f"{type(self).__name__} failed to delete run data for run "
                f"{target.id} ({detail}). The run was not deleted, to avoid "
                f"orphaning stored data. Check that the storage backend is "
                f"reachable and writable, then retry."
            )
            log.error(error_msg)
            raise RunDataDeletionError(error_msg) from failures[0][1]


def build_storage_adapter(server_config: dict) -> StorageAdapter | None:
    """Build the configured storage adapter, or return ``None`` if disabled.

    Reads two top-level keys from the server config:

    - ``large_run_data_store`` — required string, either ``"filesystem"``
      or ``"azure"``. Absent means "disabled — use the relational DB
      for inputs and results".
    - ``azure_run_data_store`` — required when ``large_run_data_store``
      is ``"azure"``; ignored otherwise.

    Raises
    ------
    ValueError
        If the deprecated ``large_result_store`` key is present (the
        config shape changed in this release), if
        ``large_run_data_store`` is not one of the supported values,
        or if ``"azure"`` is selected without an
        ``azure_run_data_store`` block.
    """
    if "large_result_store" in server_config:
        raise ValueError(
            "Configuration key 'large_result_store' is no longer supported. "
            "Use top-level 'large_run_data_store: \"filesystem\"' or "
            "'large_run_data_store: \"azure\"' (with an 'azure_run_data_store' "
            "block for the Azure credentials). See the docs at "
            "docs/features/inter-component/blob_storage.rst."
        )

    store_type = server_config.get("large_run_data_store")
    if store_type is None:
        return None

    if store_type == "filesystem":
        from vantage6.server.service.file_storage_service import (
            DEFAULT_RUN_DATA_BASE_PATH,
            RUN_DATA_BASE_PATH_ENV_VAR,
            FileStorageService,
        )

        base_path = os.environ.get(
            RUN_DATA_BASE_PATH_ENV_VAR, DEFAULT_RUN_DATA_BASE_PATH
        )
        return FileStorageService(config={}, base_path=base_path)

    if store_type == "azure":
        azure_config = server_config.get("azure_run_data_store")
        if not azure_config:
            raise ValueError(
                "large_run_data_store is 'azure' but no 'azure_run_data_store' "
                "block was provided in the server config."
            )
        from vantage6.server.service.azure_storage_service import AzureStorageService

        return AzureStorageService(config=azure_config)

    raise ValueError(
        f"Unknown large_run_data_store={store_type!r}; expected "
        f"'filesystem' or 'azure'."
    )
