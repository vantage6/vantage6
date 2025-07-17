import unittest
from unittest.mock import MagicMock, patch
from flask import Flask, Response
from vantage6.server.resource.result import ResultStream, WerkzeugChunkedStream

class TestResultStream(unittest.TestCase):
    
    def setUp(self):
        self.app = MagicMock(spec=Flask)
        self.storage_adapter = MagicMock()
        self.socketio = MagicMock()
        self.mail = MagicMock()
        self.api = MagicMock()
        self.permissions = MagicMock()
        self.config = MagicMock()
        self.result_stream = ResultStream(
            self.storage_adapter, self.socketio, self.mail, self.api, self.permissions, self.config
        )

    @patch("werkzeug.wsgi.LimitedStream")
    @patch("flask.request")
    def test_post_chunked_upload(self, mock_request):
        with self.app.test_request_context():
            mock_request.headers = {"Transfer-Encoding": "chunked"}
            mock_request.stream = MagicMock()
            mock_request.stream.read = MagicMock(return_value=b"chunked data")

            # Mock any additional attributes or methods used in post()
            self.storage_adapter.store_blob = MagicMock(return_value="mocked_uuid")

            response = self.result_stream.post()

            self.storage_adapter.store_blob.assert_called_once_with(
                unittest.mock.ANY, b"chunked data"
            )
            self.assertEqual(response[1], 201)
            self.assertIn("uuid", response[0])
            
    @patch("vantage6.server.resource.result.request")
    def test_post_non_chunked_upload(self, mock_request):
        mock_request.headers = {}
        mock_request.get_data = MagicMock(return_value=b"non-chunked data")

        response = self.result_stream.post()

        self.storage_adapter.store_blob.assert_called_once_with(
            unittest.mock.ANY, b"non-chunked data"
        )
        self.assertEqual(response[1], 201)
        self.assertIn("uuid", response[0])

    def test_get_result_streaming(self):
        blob_stream = MagicMock()
        blob_stream.chunks = MagicMock(return_value=[b"chunk1", b"chunk2"])
        self.storage_adapter.stream_blob = MagicMock(return_value=blob_stream)

        with self.app.test_request_context():
            response = self.result_stream.get("test_id")

        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["Content-Disposition"],
            "attachment; filename=result_test_id.bin"
        )

class TestWerkzeugChunkedStream(unittest.TestCase):

    def setUp(self):
        self.mock_stream = MagicMock()
        self.chunked_stream = WerkzeugChunkedStream(self.mock_stream, chunk_size=4096)

    def test_read_all_data(self):
        self.mock_stream.read = MagicMock(return_value=b"all data")
        result = self.chunked_stream.read()
        self.mock_stream.read.assert_called_once_with()
        self.assertEqual(result, b"all data")

    def test_read_with_size(self):
        self.mock_stream.read = MagicMock(return_value=b"partial data")
        result = self.chunked_stream.read(1024)
        self.mock_stream.read.assert_called_once_with(1024)
        self.assertEqual(result, b"partial data")

if __name__ == "__main__":
    unittest.main()
