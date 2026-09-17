import os
import unittest

from pathlib import Path
from unittest.mock import patch

from vantage6.common.server_context import ServerContext


class ServerContextTest(unittest.TestCase):
    """Test the database URI handling used when the server starts."""

    def setUp(self):
        self.context = object.__new__(ServerContext)
        self.context.config = {"uri": "sqlite:///default.sqlite"}
        self.context.data_dir = Path("/data")

    def test_relative_sqlite_database_uses_server_data_directory(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                "sqlite:////data/default.sqlite",
                self.context.get_database_uri(),
            )

    def test_database_uri_environment_variable_takes_precedence(self):
        uri = "postgresql://user:password@database.example/vantage6"
        with patch.dict(os.environ, {"VANTAGE6_DB_URI": uri}, clear=True):
            self.assertEqual(uri, self.context.get_database_uri())
