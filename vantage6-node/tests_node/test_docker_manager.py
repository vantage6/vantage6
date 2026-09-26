from unittest import TestCase
from unittest.mock import MagicMock

from vantage6.node.docker.docker_manager import DockerManager


def _make_manager() -> DockerManager:
    """Build a DockerManager without running the real constructor."""
    manager = DockerManager.__new__(DockerManager)
    manager.log = MagicMock()
    return manager


class TestGetColumnNames(TestCase):
    """get_column_names is unimplemented and must stay pandas-free."""

    def test_returns_empty_list_regardless_of_type(self):
        manager = _make_manager()
        for type_ in ("csv", "parquet", "sparql", "excel", "sql", "made-up-type"):
            with self.subTest(type_=type_):
                self.assertEqual(manager.get_column_names("some_label", type_), [])

    def test_does_not_touch_the_databases_attribute(self):
        # Must not depend on any manager state.
        manager = _make_manager()
        self.assertFalse(hasattr(manager, "databases"))
        self.assertEqual(manager.get_column_names("does_not_exist", "csv"), [])

    def test_logs_an_error_explaining_why(self):
        manager = _make_manager()
        manager.get_column_names("some_label", "csv")
        manager.log.error.assert_called_once()

    def test_no_pandas_or_algorithm_tools_import(self):
        import vantage6.node.docker.docker_manager as docker_manager_module

        with open(docker_manager_module.__file__) as f:
            source = f.read()
        self.assertNotIn("import pandas", source)
        self.assertNotIn("vantage6.algorithm", source)
