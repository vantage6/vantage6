from collections.abc import Callable
from importlib import import_module
from typing import TYPE_CHECKING

import pandas as pd

from vantage6.common.enum import AlgorithmStepType
from vantage6.common.globals import ContainerEnvNames

from vantage6.algorithm.tools.exceptions import (
    AlgorithmModuleNotFoundError,
    MethodNotFoundError,
    SessionActionMismatchError,
)

from vantage6.algorithm.mock.client import MockAlgorithmClient
from vantage6.algorithm.mock.globals import MockDatabase
from vantage6.algorithm.mock.util import env_vars
from vantage6.node.k8s.exceptions import DataFrameNotFound

if TYPE_CHECKING:
    from vantage6.algorithm.mock.network import MockNetwork


class MockNode:
    def __init__(
        self,
        id_: int,
        organization_id: int,
        collaboration_id: int,
        databases: list[MockDatabase],
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
        databases : list[MockDatabase]
            The databases of the node.
        network : MockNetwork
            The network that the node belongs to.
        """
        self.id_ = id_
        self.organization_id = organization_id
        self.collaboration_id = collaboration_id
        self.datasets = databases
        self.network = network

        # For whenever a user creates a dataframe
        self.dataframes = {}

        # In case a pandas dataframe is provided we assume the user directly wants to
        # use it rather than running an extraction job first.
        for dataset in self.datasets:
            if isinstance(dataset.database, pd.DataFrame):
                self.dataframes[dataset.label] = dataset.database

        # Environment variables that are passed on the execution of the algorithm
        self.env = {
            ContainerEnvNames.NODE_ID.value: self.id_,
            ContainerEnvNames.ORGANIZATION_ID.value: self.organization_id,
            ContainerEnvNames.COLLABORATION_ID.value: self.collaboration_id,
        }

        try:
            self.algorithm_module = import_module(self.network.module_name)
        except ModuleNotFoundError as e:
            raise AlgorithmModuleNotFoundError(
                f"Module {self.network.module_name} not found. {e}"
            )

    def simulate_task_run(
        self,
        method: str,
        arguments: dict,
        databases: list[dict] | list[list[dict]],
        action: str | None = None,
    ):
        """
        Simulate a task run which has been initiated by the `client.task.create` method.

        Parameters
        ----------
        method : str
            The name of the method that should be called.
        arguments : dict
            The arguments that should be passed to the method.
        databases :  list[dict] | list[list[dict]]
            The databases that should be used by the method. It should be a list of
            dictionaries, where each dictionary contains a 'type' and a 'dataframe_id'
            key. The 'type' key should be set to 'dataframe' and the 'dataframe_id' key
            should be set to the id of the dataframe that should be used.
        action : str | None
            The action of the task. If not provided, the action would normally be
            inferred from the algorithm store`, but for the mock node we do not have an
            algorithm store, so we infer it from the method directly. Suitable actions
            may be one of 'data_extraction', 'preprocessing', 'federated_compute',
            'central_compute' or 'postprocessing'.

        Returns
        -------
        dict
            The result of the task run.
        """
        method_fn = self._get_method_fn_from_method(method)

        step_type = self._get_step_type_from_method_fn(method_fn)
        if action and step_type != action:
            raise SessionActionMismatchError(
                f"Requested action {action.value}, but the method is a "
                f"{step_type.value} step."
            )

        task_env_vars = self._task_env_vars(action=step_type, method=method)

        # Detect which decorators are used and provide the mock client and/or mocked
        # data that is required to the method
        mocked_kwargs = {}
        if getattr(method_fn, "vantage6_algorithm_client_decorated", False):
            algorithm_client = MockAlgorithmClient(self, databases=databases)
            mocked_kwargs["mock_client"] = algorithm_client

        if getattr(method_fn, "vantage6_dataframe_decorated", False):
            mock_data = []
            # Handle both single list and list of lists input formats
            if len(databases) and isinstance(databases[0], list):
                # List of lists format
                for db_group in databases:
                    group_data = {}
                    for db in db_group:
                        label = self.network.server.get_label_for_df_id(
                            db["dataframe_id"]
                        )
                        self._validate_dataframe_exists(label)
                        group_data[label] = self.dataframes[label]
                    mock_data.append(group_data)
            else:
                # Single list format
                for db in databases:
                    label = self.network.server.get_label_for_df_id(db["dataframe_id"])
                    self._validate_dataframe_exists(label)
                    mock_data.append(self.dataframes[label])

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

        task_env_vars = self._task_env_vars(AlgorithmStepType.DATA_EXTRACTION, method)

        step_type = self._get_step_type_from_method_fn(method_fn)

        mocked_kwargs = {}
        # The `@data_extraction` decorator expects a `mock_uri` and `mock_type`
        if step_type == AlgorithmStepType.DATA_EXTRACTION.value:
            db_to_use = next(db for db in self.datasets if db.label == source_label)
            mocked_kwargs["mock_uri"] = db_to_use.database
            mocked_kwargs["mock_type"] = db_to_use.db_type
        else:
            raise SessionActionMismatchError(
                "The method is not a data extraction method."
            )

        result = self.run(
            method_fn, {**arguments, **mocked_kwargs}, task_env_vars=task_env_vars
        )
        df = result.to_pandas()
        self.dataframes[dataframe_name] = df
        return df

    def simulate_dataframe_preprocessing(
        self, dataframe_name: str, image: str, method: str, arguments: dict
    ):
        """
        Simulate a dataframe preprocessing which has been initiated by the `client.dataframe.preprocess` method.
        """
        method_fn = self._get_method_fn_from_method(method)
        task_env_vars = self._task_env_vars(AlgorithmStepType.PREPROCESSING, method)
        step_type = self._get_step_type_from_method_fn(method_fn)
        if step_type != AlgorithmStepType.PREPROCESSING.value:
            raise SessionActionMismatchError(
                "The method is not a preprocessing method."
            )

        mocked_kwargs = {}
        if getattr(method_fn, "vantage6_dataframe_decorated", False):
            mock_data = []
            if dataframe_name not in self.dataframes:
                raise DataFrameNotFound(
                    f"Dataframe with name {dataframe_name} not found."
                )
            mock_data = self.dataframes[dataframe_name].copy()

            mocked_kwargs["mock_data"] = [mock_data]

        result = self.run(
            method_fn, {**arguments, **mocked_kwargs}, task_env_vars=task_env_vars
        )
        df = result.to_pandas()

        # save the updated dataframe in the node
        self.dataframes[dataframe_name] = df
        return df

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

    def _validate_dataframe_exists(self, label: str) -> None:
        """
        Validate that a dataframe with the given label exists.

        Parameters
        ----------
        label : str
            The label of the dataframe to validate.

        Raises
        ------
        DataFrameNotFound
            If the dataframe with the given label is not found.
        """
        if label not in self.dataframes:
            raise DataFrameNotFound(f"Dataframe with label {label} not found.")

    def _get_step_type_from_method_fn(self, method_fn: Callable) -> AlgorithmStepType:
        """
        Get the step type from the method function.
        """
        step_type = getattr(method_fn, "vantage6_decorator_step_type", None)
        if not step_type:
            raise SessionActionMismatchError(
                "The method is not decorated with a vantage6 step type decorator."
            )

        return step_type

    def _get_method_fn_from_method(self, method: str) -> Callable:
        """
        Get the method function from the method name.
        """
        try:
            return getattr(self.algorithm_module, method)
        except AttributeError as e:
            raise MethodNotFoundError(f"Method {method} not found. {e}")

    def _task_env_vars(self, action: AlgorithmStepType, method: str) -> dict:
        """
        Get the task environment variables.
        """
        task_id = len(self.network.server.tasks)
        return {
            **self.env,
            ContainerEnvNames.FUNCTION_ACTION.value: action.value,
            ContainerEnvNames.ALGORITHM_METHOD.value: method,
            ContainerEnvNames.TASK_ID.value: task_id,
            ContainerEnvNames.SESSION_FOLDER.value: (f"./tmp/session/{task_id}"),
            ContainerEnvNames.SESSION_FILE.value: f"./tmp/session/{task_id}/session.parquet",
            ContainerEnvNames.INPUT_FILE.value: f"./tmp/session/{task_id}/input.parquet",
            ContainerEnvNames.OUTPUT_FILE.value: f"./tmp/session/{task_id}/output.parquet",
            ContainerEnvNames.CONTAINER_TOKEN.value: "some-jwt-token",
        }
