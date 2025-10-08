from unittest import TestCase
from unittest.mock import MagicMock, patch

import pandas as pd
import pyarrow as pa

from vantage6.common.enum import AlgorithmStepType
from vantage6.common.globals import ContainerEnvNames

from vantage6.mock.node import MockNode


class TestMockNodeDataframe(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.data = pd.DataFrame({"id": [1, 2, 3], "value": [10, 20, 30]})
        self.datasets = {"label_1": {"database": self.data, "db_type": "csv"}}
        self.network = MagicMock()
        self.node = MockNode(
            id_=0,
            organization_id=0,
            collaboration_id=1,
            datasets=self.datasets,
            network=self.network,
        )

    def test_initialization(self):
        """Test if node is properly initialized"""
        self.assertEqual(self.node.id_, 0)
        self.assertEqual(self.node.organization_id, 0)
        self.assertEqual(self.node.collaboration_id, 1)
        self.assertEqual(len(self.node.datasets), 1)
        self.assertIn("label_1", self.node.datasets)
        pd.testing.assert_frame_equal(self.node.dataframes["label_1"], self.data)

    def test_simulate_task_run(self):
        """Test if task run simulation works properly"""

        # Create a mock method function
        mock_method = MagicMock()
        mock_method.vantage6_decorator_step_type = (
            AlgorithmStepType.FEDERATED_COMPUTE.value
        )
        mock_method.return_value = {"result": "test"}

        # Patch the _get_method_fn_from_method to return our mock
        with patch(
            "vantage6.mock.node.MockNode._get_method_fn_from_method",
            return_value=mock_method,
        ):
            # Simulate running a task
            result = self.node.simulate_task_run(
                method="test_method",
                arguments={"arg1": "value1"},
                databases=[{"label": "label_1"}],
                action=AlgorithmStepType.FEDERATED_COMPUTE.value,
            )

            # Verify the result
            self.assertEqual(result, {"result": "test"})

    def test_run(self):
        """Test if run method works properly"""
        # Create a mock method function
        mock_method = MagicMock()
        mock_method.return_value = {"result": "test"}

        # Create mock arguments and environment variables
        mock_args = {"arg1": "value1"}
        mock_env_vars = {"env1": "value1"}

        # Test running with environment variables
        with patch("vantage6.mock.node.env_vars") as mock_env:
            result = self.node.run(mock_method, mock_args, task_env_vars=mock_env_vars)

            # Check if environment variables were set correctly
            mock_env.assert_called_once_with(**mock_env_vars)

            # Check if method was called with correct arguments
            mock_method.assert_called_once_with(**mock_args)

            # Verify the result
            self.assertEqual(result, {"result": "test"})

        # Test running without environment variables
        mock_method.reset_mock()
        result = self.node.run(mock_method, mock_args)

        # Check if method was called with correct arguments
        mock_method.assert_called_once_with(**mock_args)

        # Verify the result
        self.assertEqual(result, {"result": "test"})

    def test_simulate_dataframe_creation(self):
        """Test if simulate_dataframe_creation works properly"""
        # Create a mock method function with data extraction decorator
        mock_method = MagicMock()
        mock_method.vantage6_decorator_step_type = (
            AlgorithmStepType.DATA_EXTRACTION.value
        )
        mock_method.return_value = pa.Table.from_pandas(
            pd.DataFrame({"col1": [1, 2, 3]})
        )

        # Patch the _get_method_fn_from_method to return our mock
        with patch(
            "vantage6.mock.node.MockNode._get_method_fn_from_method",
            return_value=mock_method,
        ):
            # Simulate creating a dataframe
            self.node.simulate_dataframe_creation(
                method="test_method",
                arguments={"arg1": "value1"},
                source_label="label_1",
                dataframe_name="test_df",
            )

            # Verify the method was called with correct arguments
            mock_method.assert_called_once_with(
                arg1="value1",
                mock_uri=self.datasets["label_1"]["database"],
                mock_type=self.datasets["label_1"]["db_type"],
            )

            # Verify the dataframe was stored
            self.assertIn("test_df", self.node.dataframes)
            pd.testing.assert_frame_equal(
                self.node.dataframes["test_df"], pd.DataFrame({"col1": [1, 2, 3]})
            )

    def test_get_step_type_from_method_fn(self):
        """Test if _get_step_type_from_method_fn works properly"""
        # Create a mock method with step type decorator
        mock_method = MagicMock()
        mock_method.vantage6_decorator_step_type = (
            AlgorithmStepType.FEDERATED_COMPUTE.value
        )

        # Get step type
        step_type = self.node._get_step_type_from_method_fn(mock_method)

        # Verify correct step type is returned
        self.assertEqual(step_type, AlgorithmStepType.FEDERATED_COMPUTE.value)

        # Test method without decorator
        mock_method_no_decorator = MagicMock()
        mock_method_no_decorator.vantage6_decorator_step_type = None

        # Get step type - should return None since no decorator
        with patch('vantage6.mock.node.error'):  # Suppress print output
            step_type = self.node._get_step_type_from_method_fn(mock_method_no_decorator)

        # Verify None is returned when no decorator present
        self.assertIsNone(step_type)

    def test_get_method_fn_from_method(self):
        """Test if _get_method_fn_from_method works properly"""
        # Create a mock module with test method
        mock_module = MagicMock()
        mock_method = MagicMock()
        mock_module.test_method = mock_method

        # Mock import_module to return our mock module
        with patch(
            "vantage6.mock.node.import_module", return_value=mock_module
        ) as mock_import:
            # Set module name on network mock
            self.network.module_name = "test_module"

            # Get method function
            method_fn = self.node._get_method_fn_from_method("test_method")

            # Verify import_module was called with correct module name
            mock_import.assert_called_once_with("test_module")

            # Verify correct method was returned
            self.assertEqual(method_fn, mock_method)

    def test_task_env_vars(self):
        """Test if _task_env_vars returns correct environment variables"""
        # Mock the server tasks to simulate task count
        self.network.server.tasks = [1, 2, 3]  # 3 existing tasks

        # Call _task_env_vars with test values
        action = "compute"
        method = "test_method"
        env_vars = self.node._task_env_vars(action, method)

        # Verify all environment variables are set correctly
        expected_task_id = 3
        self.assertEqual(env_vars[ContainerEnvNames.NODE_ID.value], self.node.id_)
        self.assertEqual(
            env_vars[ContainerEnvNames.ORGANIZATION_ID.value], self.node.organization_id
        )
        self.assertEqual(
            env_vars[ContainerEnvNames.COLLABORATION_ID.value],
            self.node.collaboration_id,
        )
        self.assertEqual(env_vars[ContainerEnvNames.FUNCTION_ACTION.value], action)
        self.assertEqual(env_vars[ContainerEnvNames.ALGORITHM_METHOD.value], method)
        self.assertEqual(env_vars[ContainerEnvNames.TASK_ID.value], expected_task_id)


class TestMockNodeURI(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.datasets = {"label_1": {"database": "mock_data.csv", "db_type": "csv"}}
        self.network = MagicMock()
        self.node = MockNode(
            id_=0,
            organization_id=0,
            collaboration_id=1,
            datasets=self.datasets,
            network=self.network,
        )

    def test_initialization(self):
        """Test if node is properly initialized"""
        self.assertEqual(self.node.id_, 0)
        self.assertEqual(self.node.organization_id, 0)
        self.assertEqual(self.node.collaboration_id, 1)
        self.assertEqual(len(self.node.datasets), 1)
        self.assertIn("label_1", self.node.datasets)
        self.assertEqual(self.node.datasets["label_1"]["database"], "mock_data.csv")
        self.assertEqual(len(self.node.dataframes), 0)

    def test_node_network_reference(self):
        """Test if node has proper reference to network"""
        self.assertIs(self.node.network, self.network)
