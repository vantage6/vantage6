import base64
import json

from unittest import TestCase
from unittest.mock import patch, MagicMock

from vantage6.client import UserClient
from vantage6.common.globals import STRING_ENCODING

# Mock server
HOST = "mock_server"
PORT = 1234

# Mock credentials
FAKE_USERNAME = "vantage6_test"
FAKE_PASSWORD = "secretpassword"
FAKE_ID = 1

TASK_NAME = "test-task"
TASK_IMAGE = "mock-image"
COLLABORATION_ID = 1
ORGANIZATION_IDS = [1]
SAMPLE_INPUT = {"method": "test-task"}
FAKE_NAME = "john doe"


class TestClient(TestCase):
    def test_post_task(self):
        post_input = TestClient.post_task_on_mock_client(SAMPLE_INPUT)
        decoded_input = base64.b64decode(post_input)
        assert b'{"method": "test-task"}' == decoded_input

    def test_get_results(self):
        mock_result = json.dumps({"some_key": "some_value"}).encode()

        results = TestClient._receive_results_on_mock_client(mock_result)

        assert results == [{"result": {"some_key": "some_value"}}]

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
        with patch.multiple("vantage6.client", requests=mock_requests, jwt=mock_jwt):
            client = TestClient.setup_client()

            client.task.create(
                name=TASK_NAME,
                image=TASK_IMAGE,
                collaboration_id=COLLABORATION_ID,
                organization_ids=ORGANIZATION_IDS,
                input_=input_,
            )

            # In a request.post call, json is provided with the keyword
            # argument 'json'. call_args provides a tuple with positional
            # arguments followed by a dict with positional arguments
            post_content = mock_requests.post.call_args[1]["json"]

            post_input = post_content["organizations"][0]["input"]

        return post_input

    @staticmethod
    def _receive_results_on_mock_client(mock_result):
        mock_result = base64.b64encode(mock_result).decode(STRING_ENCODING)
        mock_result_response = [{"result": mock_result}]
        mock_jwt = TestClient._create_mock_jwt()

        mock_requests = MagicMock()
        mock_requests.get.return_value.status_code = 200
        mock_requests.post.return_value.status_code = 200

        user = {"id": FAKE_ID, "firstname": "naam", "organization": {"id": FAKE_ID}}
        organization = {"id": FAKE_ID, "name": FAKE_NAME}

        # The client will first send a post request for authentication, then
        # for retrieving results.
        mock_requests.get.return_value.json.side_effect = [
            user,
            organization,
            mock_result_response,
        ]

        with patch.multiple("vantage6.client", requests=mock_requests, jwt=mock_jwt):
            client = TestClient.setup_client()

            results = client.result.from_task(task_id=FAKE_ID)

            return results

    @staticmethod
    def setup_client() -> UserClient:
        client = UserClient(HOST, PORT)
        client.authenticate(FAKE_USERNAME, FAKE_PASSWORD)
        client.setup_encryption(None)
        return client

    @staticmethod
    def _create_mock_jwt() -> MagicMock:
        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = {"sub": FAKE_ID}
        return mock_jwt
