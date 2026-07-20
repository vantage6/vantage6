import logging
from unittest.mock import MagicMock, patch

from vantage6.common import logger_name

from vantage6.hq.websockets import DefaultSocketNamespace

from .test_resource_base import TestResourceBase

logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestSocketNamespaceCleanup(TestResourceBase):
    """
    Socket handlers must always release their database session, including when the
    handler body raises. A leaked session keeps a connection checked out for the
    lifetime of the greenlet.

    See https://github.com/vantage6/vantage6/issues/2656.
    """

    # Handlers that clean up their own session, with an argument set to call them by.
    HANDLERS_WITH_ARGS = {
        "on_algorithm_status_change": ({"run_id": 1},),
        "on_algorithm_log": ({"run_id": 1, "log": "boom"},),
        "on_node_info_update": ({"some_key": "some_value"},),
        "on_node_metrics_update": ({"cpu": 1},),
        "on_dataframe_deleted": ({"df_name": "df", "session_id": 1, "node_id": 1},),
        "on_ping": (),
    }

    def setUp(self):
        super().setUp()
        self.namespace = DefaultSocketNamespace("/tasks", MagicMock(), MagicMock())

    def test_cleanup_runs_when_handler_raises(self):
        for handler_name, args in self.HANDLERS_WITH_ARGS.items():
            with self.subTest(handler=handler_name):
                # `session` is a werkzeug LocalProxy, so it must be replaced with
                # `new=` rather than autospecced - patch() would try to resolve the
                # proxy, which fails outside a request context.
                with (
                    patch(
                        "vantage6.hq.websockets.DatabaseSessionManager"
                    ) as mock_session_manager,
                    patch.object(DefaultSocketNamespace, "_is_node", return_value=True),
                    patch("vantage6.hq.websockets.db") as mock_db,
                    patch("vantage6.hq.websockets.session", new=MagicMock()),
                ):
                    # Make the handler body blow up part-way through.
                    mock_db.Run.get.side_effect = RuntimeError("boom")
                    mock_db.Node.get_by_keycloak_id.side_effect = RuntimeError("boom")
                    mock_db.Authenticatable.get_by_keycloak_id.side_effect = (
                        RuntimeError("boom")
                    )

                    handler = getattr(self.namespace, handler_name)
                    with self.assertRaises(Exception):
                        handler(*args)

                    mock_session_manager.clear_session.assert_called_once()
