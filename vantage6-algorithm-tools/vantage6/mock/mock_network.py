from ast import Call
import json
from copy import deepcopy
from datetime import datetime
from importlib import import_module
from typing import Any, Callable

import pandas as pd

from vantage6.common import error
from vantage6.common.enum import AlgorithmStepType
from vantage6.common.globals import AuthStatus, ContainerEnvNames

from vantage6.mock.util import env_vars


class MockNetwork:
    def __init__(
        self,
        module_name: str,
        datasets: dict[str, dict[str, str | pd.DataFrame]],
        collaboration_id: int | None = 1,
        organization_ids: list[int] | None = None,
        node_ids: list[int] | None = None,
    ):
        """
        Create a mock network to test algorithms.

        This MockNetwork contains all components to simulate algorithm execution in a
        vantage6 network.

        In the case that you do not want to execute a data extraction step, you can
        provide a pandas DataFrame instead of a string for the database value.

        Parameters
        ----------
        module_name : str
            The name of the module that contains the algorithm.
        datasets : dict[str, dict[str, str | pd.DataFrame]]
            A dictionary that contains the datasets for each organization. The keys
            are the labels of the datasets used instead of the label specified in the
            node configuration. The values are either a string (path to file or SQL
            connection string) or a pandas DataFrame.
        collaboration_id : int | None
            The id of the collaboration.
        organization_ids : list[int] | None
            The ids of the organizations. By default, the ids are set to the range of
            the number of datasets.
        node_ids : list[int] | None
            The ids of the nodes. By default, the ids are set to the range of the number
            of datasets.

        Attributes
        ----------
        nodes : list[MockNode]
            The nodes of the mock network.
        server : MockServer
            The server of the mock network.
        user_client : MockUserClient
            The user client of the mock network.
        algorithm_client : MockAlgorithmClient
            The algorithm client of the mock network.
        organization_ids : list[int]
            The ids of the organizations.
        collaboration_id : int
            The id of the collaboration.
        module_name : str
            The name of the module that contains the algorithm.

        Examples
        --------
        >>> from vantage6.mock.mock_network import MockNetwork
        >>> network = MockNetwork(
        >>>     module_name="my_algorithm",
        >>>     datasets={"dataset_1": {"database": "mock_data.csv", "db_type": "csv"}},
        >>> )
        >>> client = network.user_client
        >>> client.create_new_task(
        >>>     input_={
        >>>         "method": "my_method",
        >>>         "kwargs": {"dataset": "dataset_1"},
        >>>     },
        >>> )
        >>> results = client.result.from_task(task.get("id"))
        >>> print(results)
        """

        if organization_ids and len(organization_ids) != len(datasets.keys()):
            error(
                f"The number of organization ids {len(organization_ids)} does not match "
                f"the number of datasets {len(datasets.keys())}"
            )
            return

        if node_ids and len(node_ids) != len(datasets.keys()):
            error(
                f"The number of node ids {len(node_ids)} does not match the number of "
                f"datasets {len(datasets.keys())}"
            )

        self.collaboration_id = collaboration_id
        self.module_name = module_name
        self.nodes = []

        organization_ids = (
            organization_ids if organization_ids else list(range(len(datasets)))
        )
        node_ids = node_ids if node_ids else list(range(len(datasets)))
        for org_id, node_id, dataset in zip(organization_ids, node_ids, datasets):
            self.nodes.append(
                MockNode(node_id, org_id, collaboration_id, dataset, self)
            )

        self.server = MockServer(collaboration_id)
        self.user_client = MockUserClient(self)
        self.algorithm_client = MockAlgorithmClient(self)

    @property
    def organization_ids(self) -> list[int]:
        """
        The ids of the organizations.

        Returns
        -------
        list[int]
            The ids of the organizations.
        """
        return [node.organization_id for node in self.nodes]

    @property
    def node_ids(self) -> list[int]:
        """
        The ids of the nodes.

        Returns
        -------
        list[int]
            The ids of the nodes.
        """
        return [node.id_ for node in self.nodes]

    def get_node(self, id_: int) -> "MockNode":
        """
        Get the node with the given id.

        Parameters
        ----------
        id_ : int
            The id of the node.

        Returns
        -------
        MockNode
            The node with the given id.
        """
        return next(node for node in self.nodes if node.id_ == id_)


class MockServer:
    def __init__(self, collaboration_id: int):
        """
        Create a mock server.

        Typically, you do not need to create a mock server manually. Instead, you should
        use the MockNetwork class to create a mock network.

        Parameters
        ----------
        collaboration_id : int
            The id of the collaboration.
        """

        # These contain the task, runs and results as dictionaries that are the same
        # format as you would get from the server responses.
        self.tasks = []
        self.runs = []
        self.results = []

        # We only consider one collaboration and one session as we are typically mocking
        # the algorithms in a single session TODO check wether we really need these
        self.collaboration_id = collaboration_id
        self.session_id = 1
        self.study_id = 1

    def _store_result(self, result: Any, task_id: int):
        last_result_id = len(self.results) + 1
        result = {
            "id": last_result_id,
            "result": json.dumps(result),
            "run": {
                "id": last_result_id,
                "link": f"/api/run/{last_result_id}",
                "methods": ["GET", "PATCH"],
            },
            "task": {
                "id": task_id,
                "link": f"/api/task/{task_id}",
                "methods": ["GET", "PATCH"],
            },
        }
        self.results.append(result)
        return result

    def _store_run(self, arguments: dict, task_id: int, result_id: int, org_id: int):
        last_run_id = len(self.runs) + 1
        run = {
            "id": last_run_id,
            "started_at": datetime.now().isoformat(),
            "assigned_at": datetime.now().isoformat(),
            "finished_at": datetime.now().isoformat(),
            "log": "mock_log",
            "ports": [],
            "status": "completed",
            "arguments": json.dumps(arguments),
            "results": {
                "id": result_id,
                "link": f"/api/result/{result_id}",
                "methods": ["GET", "PATCH"],
            },
            "node": {
                "id": org_id,
                "name": "mock_node",
                "status": AuthStatus.ONLINE.value,
            },
            "organization": {
                "id": 0,
                "link": "/api/organization/0",
                "methods": ["GET", "PATCH"],
            },
            "task": {
                "id": task_id,
                "link": f"/api/task/{task_id}",
                "methods": ["GET", "PATCH"],
            },
        }
        self.runs.append(run)
        return run

    def _store_task(
        self,
        init_organization_id: int,
        name: str,
        description: str,
        databases: list[dict[str, str]],
    ):
        new_task_id = len(self.tasks) + 1
        task = {
            "id": new_task_id,
            "runs": f"/api/run?task_id={new_task_id}",
            "results": f"/api/results?task_id={new_task_id}",
            "status": "completed",
            "name": name,
            "databases": databases,
            "description": description,
            "image": "mock_image",
            "init_user": {
                "id": 1,
                "link": "/api/user/1",
                "methods": ["GET", "DELETE", "PATCH"],
            },
            "init_org": {
                "id": init_organization_id,
                "link": f"/api/organization/{init_organization_id}",
                "methods": ["GET", "PATCH"],
            },
            "parent": None,
            "collaboration": {
                "id": self.collaboration_id,
                "link": f"/api/collaboration/{self.collaboration_id}",
                "methods": ["DELETE", "PATCH", "GET"],
            },
            "job_id": 1,
            "children": None,
        }
        self.tasks.append(task)
        return task


class MockNode:
    def __init__(
        self,
        id_: int,
        organization_id: int,
        collaboration_id: int,
        datasets: dict[str, dict[str, str] | pd.DataFrame],
        network: "MockNetwork",
    ):
        """
        Create a mock node.

        Typically, you do not need to create a mock node manually. Instead, you should
        use the MockNetwork class to create a mock network.

        Parameters
        ----------
        id_ : int
            The id of the node.
        organization_id : int
            The id of the organization.
        collaboration_id : int
            The id of the collaboration.
        datasets : dict[str, dict[str, str] | pd.DataFrame]
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
            if isinstance(dataset, pd.DataFrame):
                self.dataframes[label] = dataset

        # Environment variables that are passed on the execution of the algorithm
        self.env = {
            ContainerEnvNames.NODE_ID.value: self.id_,
            ContainerEnvNames.ORGANIZATION_ID.value: self.organization_id,
            ContainerEnvNames.COLLABORATION_ID.value: self.collaboration_id,
        }

    def _get_step_type_from_method_fn(self, method_fn: Callable) -> AlgorithmStepType:
        step_type = getattr(method_fn, "vantage6_decorator_step_type", None)
        if not step_type:
            error("The method is not decorated with a vantage6 step type decorator.")
            # TODO we need to raise or exit here
            return
        return step_type

    def _get_method_fn_from_method(self, method: str) -> Callable:
        module = import_module(self.network.module_name)
        return getattr(module, method)

    def _task_env_vars(self, action: str, method: str) -> dict:
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
            ContainerEnvNames.CONTAINER_TOKEN.value: "TODO",
        }

    def simulate_task_run(
        self,
        method: str,
        arguments: dict,
        databases: list[dict[str, str]],
        action: AlgorithmStepType,
    ):
        method_fn = self._get_method_fn_from_method(method)

        # Every function should have at least a step type decorator, for example:
        # @data_extraction
        # def my_function(connection_details: str):
        #     pass
        step_type = self._get_step_type_from_method_fn(method_fn)

        if not AlgorithmStepType.is_compute(step_type):
            error("Trying to run a task that is not a compute step.")
            # TODO we need to raise or exit here
            return

        task_env_vars = self._task_env_vars(action, method)

        # Detect which decorators are used and provide the mock client and/or mocked
        # data that is required to the method
        mocked_kwargs = {}
        if getattr(method_fn, "vantage6_algorithm_client_decorated", False):
            # When creating a child task, pass the parent's datasets and
            # client to the child. By passing also the client, the child
            # has access to the same IDs specified
            client_copy = deepcopy(self.parent)
            client_copy.node_id = self.id_
            client_copy.organization_id = self.organization_id
            mocked_kwargs["mock_client"] = client_copy

        if getattr(method_fn, "vantage6_dataframe_decorated", False):
            mock_data = []
            for db in databases:
                if db["label"] not in self.dataframes:
                    error(f"Dataframe with label {db['label']} not found.")
                    # TODO we need to raise or exit here
                    return
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
    ):
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

        return result

    def run(self, method_fn: Callable, arguments: dict, task_env_vars: dict = {}):
        with env_vars(**task_env_vars):
            return method_fn(**arguments)


class MockBaseClient:
    def __init__(self, network: MockNetwork):
        self.network = network

        self.task = self.Task(self)
        self.result = self.Result(self)
        self.run = self.Run(self)
        self.organization = self.Organization(self)
        self.collaboration = self.Collaboration(self)

        # Which organization do I belong to?
        self.organization_id = 0

    class SubClient:
        """
        Create sub groups of commands using this SubClient

        Parameters
        ----------
        parent : MockBaseClient
            The parent client
        """

        def __init__(self, parent) -> None:
            self.parent: MockBaseClient = parent

    def wait_for_results(self, task_id: int, interval: float = 1) -> list:
        return self.result.from_task(task_id)

    class Task(SubClient):
        """
        Task subclient for the MockAlgorithmClient
        """

        def __init__(self, parent) -> None:
            super().__init__(parent)
            self.last_result_id = 0

        def create(
            self,
            organizations: list[int],
            method: str,
            name: str = "mock",
            description: str = "mock",
            databases: list[list[dict]] | list[dict] | None = None,
            arguments: dict | None = None,
            action: str = AlgorithmStepType.FEDERATED_COMPUTE.value,
        ) -> dict:
            """
            Create a new task with the MockProtocol and return the task id.

            Parameters
            ----------
            method : str
                The name of the method that should be called.
            organizations : list[int]
                A list of organization ids that should run the algorithm.
            databases : list[list[dict]] | list[dict] | None, optional
                Databases to be used at the node. Each dict should contain
                at least a 'label' key. If a list of lists is provided, the first
                list is the databases that are required for the first argument, the
                second list is the databases that are required for the second
                argument, etc.
            arguments : dict | None
                Arguments for the algorithm method. The dictionary should contain
                the same keys as the arguments of the algorithm method.
            name : str, optional
                The name of the task, by default "mock"
            description : str, optional
                The description of the task, by default "mock"
            action : str, optional
                The action of the task, by default "federated_compute"

            Returns
            -------
            task
                A dictionary with information on the created task.
            """
            if not organizations:
                raise ValueError(
                    "No organization ids provided. Cannot create a task for "
                    "zero organizations."
                )
            if not arguments:
                arguments = {}

            # new_task_id = len(self.parent.network.server.tasks) + 1

            task = self.parent.network.server._store_task(
                init_organization_id=self.parent.organization_id,
                name=name,
                description=description,
                databases=databases,
            )

            # get data for organization
            for org_id in organizations:
                node = self.parent.network.get_node(org_id)

                result = node.simulate_task_run(method, arguments, databases, action)
                result_response = self.parent.network.server._store_result(
                    result, task["id"]
                )
                self.parent.network.server._store_run(
                    arguments, task["id"], result_response["id"], org_id
                )

            return task

    class Run(SubClient):
        """
        Run subclient for the MockBaseClient
        """

        def get(self, id_: int) -> dict:
            """
            Get mocked run by ID

            Parameters
            ----------
            id_ : int
                The id of the run.

            Returns
            -------
            dict
                A mocked run.
            """
            for run in self.parent.network.server.runs:
                if run.get("id") == id_:
                    return run
            return {"msg": f"Could not find run with id {id_}"}

        def from_task(self, task_id: int) -> list[dict]:
            """
            Get mocked runs by task ID

            Parameters
            ----------
            task_id : int
                The id of the task.

            Returns
            -------
            list[dict]
                A list of mocked runs.
            """
            runs = []
            for run in self.parent.network.server.runs:
                if run.get("task").get("id") == task_id:
                    runs.append(run)
            return runs

    class Result(SubClient):
        """
        Result subclient for the MockAlgorithmClient
        """

        def get(self, id_: int) -> Any:
            """
            Get mocked result by ID

            Parameters
            ----------
            id_ : int
                The id of the result.

            Returns
            -------
            Any
                A mocked result.
            """
            for result in self.network.parent.server.results:
                if result.get("id") == id_:
                    return json.loads(result.get("result"))
            return {"msg": f"Could not find result with id {id_}"}

        def from_task(self, task_id: int) -> list[Any]:
            """
            Return the results of the task with the given id.

            Parameters
            ----------
            task_id : int
                The id of the task.

            Returns
            -------
            list[Any]
                The results of the task.
            """
            results = []
            for result in self.parent.network.server.results:
                if result.get("task").get("id") == task_id:
                    results.append(json.loads(result.get("result")))
            return results

    class Organization(SubClient):
        """
        Organization subclient for the MockBaseClient
        """

        def get(self, id_: int) -> dict:
            """
            Get mocked organization by ID

            Parameters
            ----------
            id_ : int
                The id of the organization.

            Returns
            -------
            dict
                A mocked organization.
            """
            if id_ not in self.parent.network.organization_ids:
                return {"msg": f"Organization {id_} not found."}
            return {
                "id": id_,
                "name": f"mock-{id_}",
                "domain": f"mock-{id_}.org",
                "address1": "mock",
                "address2": "mock",
                "zipcode": "mock",
                "country": "mock",
                "public_key": "mock",
                "collaborations": f"/api/collaboration?organization_id={id_}",
                "users": f"/api/user?organization_id={id_}",
                "tasks": f"/api/task?init_org_id={id_}",
                "nodes": f"/api/node?organization_id={id_}",
                "runs": f"/api/run?organization_id={id_}",
            }

        def list(self) -> list[dict]:
            """
            Get mocked organizations in the collaboration.

            Returns
            -------
            list[dict]
                A list of mocked organizations in the collaboration.
            """
            organizations = []
            for i in self.parent.network.organization_ids:
                organizations.append(self.get(i))
            return organizations

    class Collaboration(SubClient):
        """
        Collaboration subclient for the MockAlgorithmClient
        """

        def get(self, is_encrypted: bool = True) -> dict:
            """
            Get mocked collaboration

            Parameters
            ----------
            is_encrypted : bool
                Whether the collaboration is encrypted or not. Default True.

            Returns
            -------
            dict
                A mocked collaboration.
            """
            id_ = self.parent.network.server.collaboration_id
            return {
                "id": id_,
                "name": "mock-collaboration",
                "encrypted": is_encrypted,
                "tasks": f"/api/task?collaboration_id={id_}",
                "nodes": f"/api/node?collaboration_id={id_}",
                "organizations": f"/api/organization?collaboration_id={id_}",
            }


class MockUserClient(MockBaseClient):
    def __init__(self, network: "MockNetwork", *args, **kwargs):
        super().__init__(network, *args, **kwargs)
        self.network = network
        self.dataframe = self.Dataframe(self)

    class Dataframe(MockBaseClient.SubClient):
        def create(
            self,
            label: str,
            method: str,
            arguments: dict | None = None,
            name: str = "mock_dataframe",
            **kwargs,
        ) -> dict:
            """
            Not available: `image`, `session`, `store`, `display`
            """
            if not arguments:
                arguments = {}

            task = self.parent.network.server._store_task(
                init_organization_id=self.parent.organization_id,
                name=name,
                description=f"Mock dataframe creation for {label}",
                databases=[{"label": label}],
            )

            # get data for organization
            for org_id in self.parent.network.organization_ids:
                node = self.parent.network.get_node(org_id)

                node.simulate_dataframe_creation(method, arguments, label, name)
                # In case of a dataframe we do not store a result, as the dataframe
                # creation on the node is the result of this action.
                result_response = self.parent.network.server._store_result(
                    {}, task["id"]
                )
                self.parent.network.server._store_run(
                    arguments, task["id"], result_response["id"], org_id
                )

            return task


class MockAlgorithmClient(MockBaseClient):
    def __init__(self, network: "MockNetwork", *args, **kwargs):
        super().__init__(network, *args, **kwargs)
        self.network = network
