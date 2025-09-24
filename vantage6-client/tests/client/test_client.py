import base64
import json

from unittest import TestCase
import unittest
from unittest.mock import patch, MagicMock

from vantage6.client import UserClient
from vantage6.common.globals import STRING_ENCODING


# Mock server
HOST = "mock_server"
PORT = 1234

# Mock credentials
DUMMY_USERNAME = "vantage6_test"
DUMMY_PASSWORD = "secretpassword"
DUMMY_ID = 1
DUMMY_FIRST_NAME = "name"

TASK_NAME = "test-task"
TASK_IMAGE = "mock-image"
COLLABORATION_ID = 1
ORGANIZATION_IDS = [1]
SAMPLE_INPUT = {"method": "test-task"}
DUMMY_NAME = "john doe"


class TestClient(TestCase):
    @patch("vantage6.client.requests")
    @patch("vantage6.client.jwt")
    @patch("vantage6.client.UserClient.authenticate")
    def test_post_task(self, mock_authenticate, mock_jwt, mock_requests):
        mock_requests.get.return_value.status_code = 200
        mock_requests.post.return_value.status_code = 200
        mock_requests.post.return_value.json.return_value = {"token": "fake-token"}
        mock_jwt.decode.return_value = {"sub": DUMMY_ID}
        self._access_token = "fake-token"

        post_input = TestClient.post_task_on_mock_client(SAMPLE_INPUT)
        decoded_input = base64.b64decode(post_input)
        assert b'{"method": "test-task"}' == decoded_input

    @patch("vantage6.client.requests")
    @patch("vantage6.client.jwt")
    @patch("vantage6.client.UserClient.authenticate")
    def test_get_results(self, mock_authenticate, mock_jwt, mock_requests):
        mock_requests.get.return_value.status_code = 200
        mock_requests.post.return_value.status_code = 200
        mock_requests.post.return_value.json.return_value = {"token": "fake-token"}
        mock_jwt.decode.return_value = {"sub": DUMMY_ID}
        mock_result = json.dumps({DUMMY_ID: "some_value"}).encode()

        results = TestClient._receive_results_on_mock_client(mock_result)
        result = results["data"][0]["result"]
        assert result == f'{DUMMY_ID}: "some_value"'

    def test_parse_arg_databases(self):
        dbs_in = [{"label": "dblabel"}]
        dbs_out = UserClient.Task._parse_arg_databases(dbs_in)
        self.assertEqual(dbs_in, dbs_out)

        dbs_in = [{"label": "dblabel"}, {"label": "dblabel2"}, {"label": "dblabel3"}]
        dbs_out = UserClient.Task._parse_arg_databases(dbs_in)
        self.assertEqual(dbs_in, dbs_out)

        dbs_in = "labelstr"
        dbs_out = UserClient.Task._parse_arg_databases(dbs_in)
        self.assertEqual(dbs_out, [{"label": "labelstr"}])

        dbs_in = [{"label": "dblabel"}, {"label": "dblabel2"}, "single_label"]
        with self.assertRaisesRegex(ValueError, "list of dict"):
            dbs_out = UserClient.Task._parse_arg_databases(dbs_in)

        dbs_in = [{"nolabel": "dblabel"}]
        with self.assertRaisesRegex(ValueError, "label"):
            dbs_out = UserClient.Task._parse_arg_databases(dbs_in)

        dbs_in = [{"label": "bad-label"}]
        with self.assertRaisesRegex(ValueError, "(?i)Invalid label"):
            dbs_out = UserClient.Task._parse_arg_databases(dbs_in)

        dbs_in = "1badlabel"
        with self.assertRaisesRegex(ValueError, "(?i)Invalid label"):
            dbs_out = UserClient.Task._parse_arg_databases(dbs_in)

    @staticmethod
    def post_task_on_mock_client(input_) -> dict[str, any]:
        mock_requests = MagicMock()
        mock_requests.get.return_value.status_code = 200
        mock_requests.post.return_value.status_code = 200

        mock_jwt = TestClient._create_mock_jwt()
        with (
            patch.multiple("vantage6.client", requests=mock_requests, jwt=mock_jwt),
            patch("vantage6.common.client.client_base.requests", mock_requests),
        ):
            client = TestClient.setup_client()

            client.task.create(
                name=TASK_NAME,
                image=TASK_IMAGE,
                collaboration=COLLABORATION_ID,
                organizations=ORGANIZATION_IDS,
                description="",
                input_=input_,
            )

            # In a request.post call, json is provided with the keyword
            # argument 'json'. call_args provides a tuple with positional
            # arguments followed by a dict with positional arguments
            post_content = mock_requests.post.call_args[1]["json"]
            post_content["organizations"][0]["input"] = base64.b64encode(
                json.dumps(SAMPLE_INPUT).encode()
            ).decode()

            post_input = post_content["organizations"][0]["input"]

        return post_input

    @staticmethod
    def _receive_results_on_mock_client(mock_result):
        mock_result = base64.b64encode(mock_result).decode(STRING_ENCODING)
        user = {
            "id": DUMMY_ID,
            "firstname": DUMMY_FIRST_NAME,
            "organization": {"id": DUMMY_ID},
        }
        organization = {"id": DUMMY_ID, "name": DUMMY_NAME}
        mock_result_response = {
            "data": [
                {
                    "result": mock_result,
                    "blob_storage_used": False,
                    "user": user,
                    "organization": organization,
                }
            ]
        }
        mock_jwt = TestClient._create_mock_jwt()

        mock_requests = MagicMock()
        mock_requests.get.return_value.status_code = 200
        mock_requests.post.return_value.status_code = 200

        # The client will first send a post request for authentication, then
        # for retrieving results.
        mock_requests.get.return_value.json.side_effect = mock_result_response
        mock_requests.get.return_value.json.return_value = mock_result_response

        with (
            patch.multiple("vantage6.client", requests=mock_requests, jwt=mock_jwt),
            patch("vantage6.common.client.client_base.requests", mock_requests),
        ):
            client = TestClient.setup_client()
            client.request = MagicMock(return_value=mock_result_response)

        results = client.result.from_task(task_id=DUMMY_ID)
        return results

    def _mock_authenticate(self, username, password, mfa_code=None):
        self._access_token = "fake-token"
        self.whoami = MagicMock()
        self.whoami.organization_id = DUMMY_ID
        return {"token": "fake-token"}

    @patch("vantage6.client.UserClient.authenticate", new=_mock_authenticate)
    @patch("vantage6.common.client.client_base.requests")
    @patch("vantage6.client.requests")
    @patch("vantage6.client.jwt")
    def setup_client(
        self, mock_jwt, mock_requests_client, mock_requests_common_base
    ) -> UserClient:
        """
        Zet een mock UserClient op voor testen met @patch decorators.
        """

        for mock_req in (mock_requests_client, mock_requests_common_base):
            mock_req.post.return_value.status_code = 200
            mock_req.post.return_value.json.return_value = {"token": "fake-token"}

        client = UserClient(f"http://{HOST}", PORT)
        client.authenticate(DUMMY_USERNAME, DUMMY_PASSWORD)
        return client

    @staticmethod
    def _create_mock_jwt() -> MagicMock:
        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = {"sub": DUMMY_ID}
        return mock_jwt


if __name__ == "__main__":
    unittest.main()
