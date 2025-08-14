import unittest
from unittest.mock import MagicMock, patch

from vantage6.node.docker.task_manager import DockerTaskManager

class TestDockerTaskManagerCleanup(unittest.TestCase):
    @patch("vantage6.node.docker.task_manager.AzureStorageService")
    @patch("vantage6.node.docker.task_manager.remove_container")
    def test_cleanup(self, mock_remove_container, mock_AzureStorageService):
        # Arrange
        mock_log = MagicMock()
        mock_container = MagicMock()
        mock_container.name = "test-container"
        mock_helper_container = MagicMock()
        mock_storage_service = mock_AzureStorageService.return_value

        # Create a minimal DockerTaskManager instance
        manager = object.__new__(DockerTaskManager)
        manager.log = mock_log
        manager.container = mock_container
        manager.helper_container = mock_helper_container
        manager.ctx = MagicMock()
        manager.ctx.connection_string = "test-connection-string"
        # Act
        manager.cleanup(manager.ctx)

        # Assert
        mock_log.info.assert_called_with("Delete blob for test-container from Azure Storage.")
        mock_AzureStorageService.assert_called()
        mock_storage_service.delete_blob.assert_called()
        mock_remove_container.assert_any_call(mock_helper_container, kill=True)
        mock_remove_container.assert_any_call(mock_container, kill=True)

if __name__ == "__main__":
    unittest.main()