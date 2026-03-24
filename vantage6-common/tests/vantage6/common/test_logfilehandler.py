import os
import stat
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import vantage6.common.log as log_module
from vantage6.common.log import OwnershipPreservingRotatingFileHandler


class TestOwnershipPreservingRotatingFileHandler(TestCase):
    def test_rollover_restores_file_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "node_user_test.log"
            log_file.write_text("something", encoding="utf-8")
            os.chmod(log_file, 0o640)
            # Capture metadata from the original host-side file. After rollover,
            # the newly created base file should get this metadata back.
            expected_stats = os.stat(log_file)

            handler = OwnershipPreservingRotatingFileHandler(
                log_file, maxBytes=5, backupCount=1
            )
            # Patch chmod/chown to avoid permission assumptions in CI/CT and to
            # verify that metadata restoration is attempted with the expected
            # values. Not as good a test.. but it's something.
            with patch.object(log_module.os, "chown") as mock_chown, patch.object(
                log_module.os, "chmod"
            ) as mock_chmod:
                handler.doRollover()
            handler.close()

            mock_chown.assert_called_once_with(
                handler.baseFilename, expected_stats.st_uid, expected_stats.st_gid
            )
            mock_chmod.assert_called_once_with(
                handler.baseFilename, stat.S_IMODE(expected_stats.st_mode)
            )

    def test_rollover_without_existing_file_skips_metadata_restore(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "missing.log"
            handler = OwnershipPreservingRotatingFileHandler(
                log_file, maxBytes=1, backupCount=1, delay=True
            )

            # No base file exists yet, so there is no metadata to carry over.
            with patch.object(log_module.os, "chown") as mock_chown, patch.object(
                log_module.os, "chmod"
            ) as mock_chmod:
                handler.doRollover()
            handler.close()

            mock_chown.assert_not_called()
            mock_chmod.assert_not_called()
