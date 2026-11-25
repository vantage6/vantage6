import unittest
from unittest.mock import MagicMock, patch

from vantage6.common.exceptions import ProxyRequestError

from vantage6.node import proxy_server

TOKEN = "Bearer secret-container-token"
BODY_MARKER = "sensitive-task-input"


def _error_response() -> MagicMock:
    response = MagicMock()
    response.status_code = 500
    response.headers = {"Content-Type": "application/json"}
    response.json.return_value = {"msg": "server error"}
    response.content = b'{"msg": "server error"}'
    return response


class TestProxyServerLogging(unittest.TestCase):
    def setUp(self):
        proxy_server.hq_url = "http://hq.test/api"

    def test_make_request_does_not_log_token_or_body(self):
        with (
            patch.object(proxy_server.requests, "post", return_value=_error_response()),
            self.assertLogs(proxy_server.log, level="DEBUG") as logs,
            self.assertRaises(ProxyRequestError),
        ):
            proxy_server.make_request(
                "post",
                "task",
                json={"input": BODY_MARKER},
                headers={"Authorization": TOKEN},
            )

        output = "\n".join(logs.output)
        self.assertNotIn(TOKEN, output)
        self.assertNotIn(BODY_MARKER, output)
        self.assertIn("method: POST, url: http://hq.test/api/task", output)
        self.assertIn("status code 500", output)

    def test_blobstream_get_does_not_log_token(self):
        client = proxy_server.app.test_client()
        with (
            patch.object(proxy_server.requests, "get", return_value=_error_response()),
            self.assertLogs(proxy_server.log, level="DEBUG") as logs,
        ):
            response = client.get("/blobstream/abc", headers={"Authorization": TOKEN})

        self.assertEqual(response.status_code, 500)
        output = "\n".join(logs.output)
        self.assertNotIn(TOKEN, output)
        self.assertIn("url: http://hq.test/api/blobstream/abc", output)
