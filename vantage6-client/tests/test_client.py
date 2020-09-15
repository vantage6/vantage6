import base64
import pickle
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

    @staticmethod
    def post_task_on_mock_client(input_, serialization: str):
        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = {'identity': FAKE_ID}
        mock_requests = MagicMock()
        mock_requests.get.return_value.status_code = 200
        mock_requests.post.return_value.status_code = 200
        with patch.multiple('vantage6.client', requests=mock_requests, jwt=mock_jwt):
            client = Client(HOST, PORT)
            client.authenticate(FAKE_USERNAME, FAKE_PASSWORD)
            client.setup_encryption(None)

            client.post_task(name=TASK_NAME, image=TASK_IMAGE, collaboration_id=COLLABORATION_ID,
                             organization_ids=ORGANIZATION_IDS, input_=input_, data_format=serialization)

            # In a request.post call, json is provided with the keyword argument 'json'
            # call_args provides a tuple with positional arguments followed by a dict with positional arguments
            post_content = mock_requests.post.call_args[1]['json']

            post_input = post_content['organizations'][0]['input']

        return post_input
