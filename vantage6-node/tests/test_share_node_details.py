from unittest import TestCase
from unittest.mock import MagicMock

from vantage6.node import Node
from vantage6.node.docker.docker_manager import DockerManager


def _make_node(config: dict) -> Node:
    """Build a Node without running the real constructor."""
    node = Node.__new__(Node)
    node.config = config
    node.log = MagicMock()
    # `__docker` is name-mangled since it's a dunder attribute of Node.
    node._Node__docker = MagicMock(spec=DockerManager)
    node.socketIO = MagicMock()
    return node


def _shared_payload(node: Node) -> dict:
    node.share_node_details()
    node.socketIO.emit.assert_called_once()
    args, kwargs = node.socketIO.emit.call_args
    assert args[0] == "node_info_update"
    assert kwargs.get("namespace") == "/tasks"
    return args[1]


class TestShareConfigToggle(TestCase):
    def test_share_config_false_skips_sharing_entirely(self):
        node = _make_node({"share_config": False})
        node.share_node_details()
        node.socketIO.emit.assert_not_called()

    def test_share_config_defaults_to_true(self):
        node = _make_node({})
        node.share_node_details()
        node.socketIO.emit.assert_called_once()

    def test_share_config_true_is_explicit_noop_change(self):
        node = _make_node({"share_config": True})
        node.share_node_details()
        node.socketIO.emit.assert_called_once()


class TestAllowedAlgorithmsSharing(TestCase):
    def test_not_shared_by_default(self):
        node = _make_node({"policies": {"allowed_algorithms": ["some-regex.*"]}})
        payload = _shared_payload(node)
        self.assertNotIn("allowed_algorithms", payload)

    def test_not_shared_when_explicitly_disabled(self):
        node = _make_node(
            {
                "share_allowed_algorithms": False,
                "policies": {"allowed_algorithms": ["some-regex.*"]},
            }
        )
        payload = _shared_payload(node)
        self.assertNotIn("allowed_algorithms", payload)

    def test_shared_when_enabled(self):
        node = _make_node(
            {
                "share_allowed_algorithms": True,
                "policies": {"allowed_algorithms": ["some-regex.*"]},
            }
        )
        payload = _shared_payload(node)
        self.assertEqual(payload["allowed_algorithms"], ["some-regex.*"])

    def test_defaults_to_all_when_enabled_but_policy_unset(self):
        node = _make_node({"share_allowed_algorithms": True})
        payload = _shared_payload(node)
        self.assertEqual(payload["allowed_algorithms"], "all")


class TestAllowedUsersAndOrgsSharing(TestCase):
    """Allowed users/orgs are unaffected by the new opt-in flags."""

    def test_shared_when_configured(self):
        node = _make_node(
            {
                "policies": {
                    "allowed_users": [1, 2],
                    "allowed_organizations": [3],
                }
            }
        )
        payload = _shared_payload(node)
        self.assertEqual(payload["allowed_users"], [1, 2])
        self.assertEqual(payload["allowed_orgs"], [3])

    def test_absent_when_not_configured(self):
        node = _make_node({})
        payload = _shared_payload(node)
        self.assertNotIn("allowed_users", payload)
        self.assertNotIn("allowed_orgs", payload)


class TestDatabaseLabelsAndTypesSharing(TestCase):
    """Labels and types are always shared, regardless of the new flags."""

    def test_labels_and_types_shared(self):
        node = _make_node(
            {
                "databases": [
                    {"label": "default", "type": "csv"},
                    {"label": "other", "type": "sql"},
                ]
            }
        )
        payload = _shared_payload(node)
        self.assertEqual(payload["database_labels"], ["default", "other"])
        self.assertEqual(
            payload["database_types"],
            {"db_type_default": "csv", "db_type_other": "sql"},
        )


class TestColumnNamesSharing(TestCase):
    """Column-name sharing stays unimplemented even when opted in."""

    def test_not_requested_by_default(self):
        node = _make_node({"databases": [{"label": "default", "type": "csv"}]})
        payload = _shared_payload(node)
        node._Node__docker.get_column_names.assert_not_called()
        self.assertNotIn("database_columns", payload)

    def test_not_requested_when_explicitly_disabled(self):
        node = _make_node(
            {
                "share_column_names": False,
                "databases": [{"label": "default", "type": "csv"}],
            }
        )
        node.share_node_details()
        node._Node__docker.get_column_names.assert_not_called()

    def test_requested_when_enabled_for_csv_and_parquet_only(self):
        node = _make_node(
            {
                "share_column_names": True,
                "databases": [
                    {"label": "csv_db", "type": "csv"},
                    {"label": "parquet_db", "type": "parquet"},
                    {"label": "sql_db", "type": "sql"},
                    {"label": "excel_db", "type": "excel"},
                ],
            }
        )
        node._Node__docker.get_column_names.return_value = []
        node.share_node_details()
        self.assertEqual(node._Node__docker.get_column_names.call_count, 2)
        node._Node__docker.get_column_names.assert_any_call("csv_db", "csv")
        node._Node__docker.get_column_names.assert_any_call("parquet_db", "parquet")

    def test_empty_columns_still_flatten_to_nothing_server_side(self):
        # get_column_names always returns [] (unimplemented), so this sends
        # {"columns_csv_db": []} -- documented edge case, not a bug.
        node = _make_node(
            {
                "share_column_names": True,
                "databases": [{"label": "csv_db", "type": "csv"}],
            }
        )
        node._Node__docker.get_column_names.return_value = []
        payload = _shared_payload(node)
        self.assertEqual(payload["database_columns"], {"columns_csv_db": []})


class TestEncryptionSharing(TestCase):
    def test_encryption_setting_shared_when_present(self):
        node = _make_node({"encryption": {"enabled": True}})
        payload = _shared_payload(node)
        self.assertEqual(payload["encryption"], True)

    def test_encryption_absent_when_not_configured(self):
        node = _make_node({})
        payload = _shared_payload(node)
        self.assertNotIn("encryption", payload)
