from copy import deepcopy
from importlib import import_module
from typing import TYPE_CHECKING, Callable

import pandas as pd

from vantage6.common import error
from vantage6.common.enum import AlgorithmStepType
from vantage6.common.globals import ContainerEnvNames

from vantage6.algorithm.tools.exceptions import SessionActionMismatchError

from vantage6.mock.util import env_vars
from vantage6.node.k8s.exceptions import DataFrameNotFound

if TYPE_CHECKING:
    from vantage6.mock.network import MockNetwork


class MockNode:
    def __init__(
        self,
        id_: int,
        organization_id: int,
        collaboration_id: int,
        datasets: list[dict[str, dict[str, str] | pd.DataFrame]],
        network: "MockNetwork",
    ):
        """
        Create a mock node.

        Typically, you do not need to create a mock node manually. Instead, you should
        use the ``MockNetwork`` class to create a mock network.

        Parameters
        ----------
        id_ : int
            The id of the node.
        organization_id : int
            The id of the organization.
        collaboration_id : int
            The id of the collaboration.
        datasets : list[dict[str, dict[str, str] | pd.DataFrame]]
            The datasets of the node.
        network : MockNetwork
            The network that the node belongs to.
        """
        self.id_ = id_
        self.organization_id = organization_id
        self.collaboration_id = collaboration_id
        self.datasets = datasets
        self.network = network

        # For whenever a user creates a dataframe
        self.dataframes = {}

        # In case a pandas dataframe is provided we assume the user directly wants to
        # use it rather than running an extraction job first.
        for label, dataset in datasets.items():
            if isinstance(dataset["database"], pd.DataFrame):
                self.dataframes[label] = dataset["database"]

        # Environment variables that are passed on the execution of the algorithm
        self.env = {
            ContainerEnvNames.NODE_ID.value: self.id_,
            ContainerEnvNames.ORGANIZATION_ID.value: self.organization_id,
            ContainerEnvNames.COLLABORATION_ID.value: self.collaboration_id,
        }

    def simulate_task_run(
        self,
        method: str,
        arguments: dict,
        databases: list[dict[str, str]],
        action: AlgorithmStepType,
    ):
        """
        Simulate a task run which has been initiated by the `client.task.create` method.

        Parameters
        ----------
        method : str
            The name of the method that should be called.
        arguments : dict
            The arguments that should be passed to the method.
        databases : list[dict[str, str]]
            The databases that should be used by the method. Each dict should contain
            at least a 'label' key that refers to a dataframe.
        action : AlgorithmStepType
            The action that should be performed.

        Returns
        -------
        dict
            The result of the task run.
        """
        method_fn = self._get_method_fn_from_method(method)

        # Every function should have at least a step type decorator, for example:
        # @data_extraction
        # def my_function(connection_details: str):
        #     pass
        step_type = self._get_step_type_from_method_fn(method_fn)

        if not AlgorithmStepType.is_compute(step_type):
            error("Trying to run a task that is not a compute step.")
            raise SessionActionMismatchError(
                "Trying to run a task that is not a compute step."
            )

        task_env_vars = self._task_env_vars(action, method)

        # Detect which decorators are used and provide the mock client and/or mocked
        # data that is required to the method
        mocked_kwargs = {}
        if getattr(method_fn, "vantage6_algorithm_client_decorated", False):
            # When creating a child task, pass the parent's datasets and
            # client to the child. By passing also the client, the child
            # has access to the same IDs specified
            client_copy = deepcopy(self.network.algorithm_client)
            client_copy.node_id = self.id_
            client_copy.organization_id = self.organization_id
            mocked_kwargs["mock_client"] = client_copy

        if getattr(method_fn, "vantage6_dataframe_decorated", False):
            mock_data = []
            for db in databases:
                if db["label"] not in self.dataframes:
                    error(f"Dataframe with label {db['label']} not found.")
                    raise DataFrameNotFound(
                        f"Dataframe with label {db['label']} not found."
                    )
                mock_data.append(self.dataframes[db["label"]])

            # make a copy of the data to avoid modifying the original data of
            # subsequent tasks
            mocked_kwargs["mock_data"] = [d.copy() for d in mock_data]

        result = self.run(
            method_fn,
            {**arguments, **mocked_kwargs},
            task_env_vars=task_env_vars,
        )

        return result

    def simulate_dataframe_creation(
        self, method: str, arguments: dict, source_label: str, dataframe_name: str
    ) -> None:
        """
        Simulate a dataframe creation which has been initiated by the `client.dataframe.create` method.

        Parameters
        ----------
        method : str
            The name of the method that should be called.
        arguments : dict
            The arguments that should be passed to the method.
        source_label : str
            The label of the source dataframe. This label should match the label that
            the user provided when creating the ``MockNetwork``.
        dataframe_name : str
            The name of the dataframe. This name will be used to identify the dataframe
            when using the ``client.task.create`` method.
        """
        method_fn = self._get_method_fn_from_method(method)

        task_env_vars = self._task_env_vars(
            AlgorithmStepType.DATA_EXTRACTION.value, method
        )

        step_type = self._get_step_type_from_method_fn(method_fn)

        mocked_kwargs = {}
        # The `@data_extraction` decorator expects a `mock_uri` and `mock_type`
        if step_type == AlgorithmStepType.DATA_EXTRACTION.value:
            mocked_kwargs["mock_uri"] = self.datasets[source_label]["database"]
            mocked_kwargs["mock_type"] = self.datasets[source_label]["db_type"]

        result = self.run(
            method_fn, {**arguments, **mocked_kwargs}, task_env_vars=task_env_vars
        )
        self.dataframes[dataframe_name] = result.to_pandas()

    def run(self, method_fn: Callable, arguments: dict, task_env_vars: dict = {}):
        """
        Run a method with the given arguments and task environment variables.

        Parameters
        ----------
        method_fn : Callable
            The method to run.
        arguments : dict
            The arguments to pass to the method.
        task_env_vars : dict
            The task environment variables.

        Returns
        -------
        Any
            The result of the method run.
        """
        with env_vars(**task_env_vars):
            return method_fn(**arguments)

    def _get_step_type_from_method_fn(self, method_fn: Callable) -> AlgorithmStepType:
        """
        Get the step type from the method function.
        """
        step_type = getattr(method_fn, "vantage6_decorator_step_type", None)
        if not step_type:
            error("The method is not decorated with a vantage6 step type decorator.")
            raise SessionActionMismatchError(
                "The method is not decorated with a vantage6 step type decorator."
            )

        return step_type

    def _get_method_fn_from_method(self, method: str) -> Callable:
        """
        Get the method function from the method name.
        """
        module = import_module(self.network.module_name)
        return getattr(module, method)

    def _task_env_vars(self, action: str, method: str) -> dict:
        """
        Get the task environment variables.
        """
        task_id = len(self.network.server.tasks)
        return {
            **self.env,
            ContainerEnvNames.FUNCTION_ACTION.value: action,
            ContainerEnvNames.ALGORITHM_METHOD.value: method,
            ContainerEnvNames.TASK_ID.value: task_id,
            ContainerEnvNames.SESSION_FOLDER.value: (f"./tmp/session/{task_id}"),
            ContainerEnvNames.SESSION_FILE.value: f"./tmp/session/{task_id}/session.parquet",
            ContainerEnvNames.INPUT_FILE.value: f"./tmp/session/{task_id}/input.parquet",
            ContainerEnvNames.OUTPUT_FILE.value: f"./tmp/session/{task_id}/output.parquet",
            ContainerEnvNames.CONTAINER_TOKEN.value: "some-jwt-token",
        }
