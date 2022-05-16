import base64
import json
import pickle
from typing import Dict
from unittest import TestCase
from unittest.mock import patch, MagicMock

from vantage6.client import Client

# Mock server
HOST = 'mock_server'
PORT = 1234

# Mock credentials
FAKE_USERNAME = 'vantage6_test'
FAKE_PASSWORD = 'secretpassword'
FAKE_ID = 1

TASK_NAME = 'test-task'
TASK_IMAGE = 'mock-image'
COLLABORATION_ID = 1
ORGANIZATION_IDS = [1]
SAMPLE_INPUT = {'method': 'test-task'}
FAKE_NAME = 'john doe'
STRING_ENCODING = 'utf-8'


class TestClient(TestCase):

    def test_post_task_legacy_method(self):
        post_input = TestClient.post_task_on_mock_client(SAMPLE_INPUT, 'legacy')
        decoded_input = base64.b64decode(post_input)
        decoded_input = pickle.loads(decoded_input)
        assert {'method': 'test-task'} == decoded_input

    def test_post_json_task(self):
        post_input = TestClient.post_task_on_mock_client(SAMPLE_INPUT, 'json')
        decoded_input = base64.b64decode(post_input)
        assert b'json.{"method": "test-task"}' == decoded_input

    def test_post_pickle_task(self):
        post_input = TestClient.post_task_on_mock_client(SAMPLE_INPUT, 'pickle')
        decoded_input = base64.b64decode(post_input)

        assert b'pickle.' == decoded_input[0:7]

        assert {'method': 'test-task'} == pickle.loads(decoded_input[7:])

    def test_get_legacy_results(self):
        mock_result = pickle.dumps(1)

        results = TestClient._receive_results_on_mock_client(mock_result)

        assert results == [{'result': 1}]

    def test_get_json_results(self):
        mock_result = b'json.' + json.dumps({'some_key': 'some_value'}).encode()

        results = TestClient._receive_results_on_mock_client(mock_result)

        assert results == [{'result': {'some_key': 'some_value'}}]

    def test_get_pickle_results(self):
        mock_result = b'pickle.' + pickle.dumps([1, 2, 3, 4, 5])

        results = TestClient._receive_results_on_mock_client(mock_result)

        assert results == [{'result': [1, 2, 3, 4, 5]}]

    @staticmethod
    def post_task_on_mock_client(input_, serialization: str) -> Dict[str, any]:
        mock_requests = MagicMock()
        mock_requests.get.return_value.status_code = 200
        mock_requests.post.return_value.status_code = 200

        mock_jwt = TestClient._create_mock_jwt()
        with patch.multiple('vantage6.client', requests=mock_requests, jwt=mock_jwt):
            client = TestClient.setup_client()

            client.post_task(name=TASK_NAME, image=TASK_IMAGE, collaboration_id=COLLABORATION_ID,
                             organization_ids=ORGANIZATION_IDS, input_=input_, data_format=serialization)

            # In a request.post call, json is provided with the keyword argument 'json'
            # call_args provides a tuple with positional arguments followed by a dict with positional arguments
            post_content = mock_requests.post.call_args[1]['json']

            post_input = post_content['organizations'][0]['input']

        return post_input

    @staticmethod
    def _receive_results_on_mock_client(mock_result):
        mock_result = base64.b64encode(mock_result).decode(STRING_ENCODING)
        mock_result_response = [{'result': mock_result}]
        mock_jwt = TestClient._create_mock_jwt()

        mock_requests = MagicMock()
        mock_requests.get.return_value.status_code = 200
        mock_requests.post.return_value.status_code = 200

        user = {'id': FAKE_ID, 'firstname': 'naam', 'organization': {'id': FAKE_ID}}
        organization = {'id': FAKE_ID, 'name': FAKE_NAME}

        # The client will first send a post request for authentication, then for retrieving results.
        mock_requests.get.return_value.json.side_effect = [user, organization, mock_result_response]

        with patch.multiple('vantage6.client', requests=mock_requests, jwt=mock_jwt):
            client = TestClient.setup_client()

            results = client.result.from_task(task_id=FAKE_ID)

            return results

    @staticmethod
    def setup_client() -> Client:
        client = Client(HOST, PORT)
        client.authenticate(FAKE_USERNAME, FAKE_PASSWORD)
        client.setup_encryption(None)
        return client

    @staticmethod
    def _create_mock_jwt() -> MagicMock:
        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = {'identity': FAKE_ID}
        return mock_jwt
