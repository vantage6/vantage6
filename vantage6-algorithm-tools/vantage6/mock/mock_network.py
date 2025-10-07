import json
import os
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from importlib import import_module
from typing import Any, Optional

import pandas as pd

from vantage6.common import error
from vantage6.common.enum import AlgorithmStepType
from vantage6.common.globals import AuthStatus, ContainerEnvNames


@contextmanager
def env_vars(**kwargs):
    """Context manager to temporarily set environment variables"""
    old_values = {}
    try:
        for key, value in kwargs.items():
            old_values[key] = os.environ.get(key)
            os.environ[key] = str(value)
        yield
    finally:
        for key, old_value in old_values.items():
            if old_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old_value


class MockNetwork:
    """
    Mock a server with a single collaboration and a set of organizations.
    """

    def __init__(
        self,
        module_name: str,
        datasets: dict[str, dict[str, str]],
        collaboration_id: Optional[int] = 1,
        organization_ids: Optional[list[int]] = None,
        node_ids: Optional[list[int]] = None,
    ):
        self.collaboration_id = collaboration_id
        self.module_name = module_name

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

        organization_ids = (
            organization_ids if organization_ids else list(range(len(datasets)))
        )
        node_ids = node_ids if node_ids else list(range(len(datasets)))

        self.nodes = []
        for org_id, node_id, dataset in zip(organization_ids, node_ids, datasets):
            self.nodes.append(MockNode(node_id, org_id, collaboration_id, dataset))

        self.server = MockServer(collaboration_id)

    @property
    def organization_ids(self) -> list[int]:
        return [node.organization_id for node in self.nodes]

    @property
    def node_ids(self) -> list[int]:
        return [node.id_ for node in self.nodes]

    def get_node(self, id_: int) -> "MockNode":
        return next(node for node in self.nodes if node.id_ == id_)


class MockServer:
    def __init__(self, collaboration_id: int):
        self.tasks = []
        self.runs = []
        self.results = []

        # We only consider one collaboration and one session as we are typically mocking
        # the algorithms in a single session TODO check wether we really need these
        self.collaboration_id = collaboration_id
        self.session_id = 1
        self.study_id = 1


class MockNode:
    def __init__(
        self,
        id_: int,
        organization_id: int,
        collaboration_id: int,
        datasets: dict[str, dict[str, str] | pd.DataFrame],
    ):
        self.id_ = id_
        self.organization_id = organization_id
        self.collaboration_id = collaboration_id
        self.datasets = datasets

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

    def run(self, method: str, arguments: dict):
        with env_vars(**self.env):
            result = method(**arguments)
        return result


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
            arguments: dict | None = None,
            action: str = AlgorithmStepType.FEDERATED_COMPUTE.value,
        ) -> int:
            """
            Create a new task with the MockProtocol and return the task id.

            Parameters
            ----------
            method : str
                The name of the method that should be called.
            organizations : list[int]
                A list of organization ids that should run the algorithm.
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

            # get algorithm function from module
            module = import_module(self.parent.network.module_name)
            method_fn = getattr(module, method)

            new_task_id = len(self.parent.network.server.tasks) + 1

            # get data for organization
            for org_id in organizations:
                # When creating a child task, pass the parent's datasets and
                # client to the child. By passing also the client, the child
                # has access to the same IDs specified
                node = self.parent.network.get_node(org_id)
                data = node.datasets
                client_copy = deepcopy(self.parent)
                client_copy.node_id = node.id_
                client_copy.organization_id = org_id

                # detect which decorators are used and provide the mock client
                # and/or mocked data that is required to the method
                mocked_kwargs = {}
                if getattr(method_fn, "vantage6_algorithm_client_decorated", False):
                    mocked_kwargs["mock_client"] = client_copy
                if getattr(method_fn, "vantage6_dataframe_decorated", False):
                    # make a copy of the data to avoid modifying the original data of
                    # subsequent tasks
                    mocked_kwargs["mock_data"] = [d.copy() for d in data]
                elif getattr(method_fn, "vantage6_decorator_step_type", False):
                    # TODO
                    mocked_kwargs["mock_uri"] = data["test_data_1"]["database"]
                    mocked_kwargs["mock_type"] = data["test_data_1"]["db_type"]

                task_env_vars = {
                    **node.env,
                    ContainerEnvNames.FUNCTION_ACTION.value: action,
                    ContainerEnvNames.TASK_ID.value: new_task_id,
                    ContainerEnvNames.ALGORITHM_METHOD.value: method,
                    ContainerEnvNames.SESSION_FOLDER.value: \
                        f"./tmp/session/{new_task_id}",
                    ContainerEnvNames.SESSION_FILE.value: \
                        f"./tmp/session/{new_task_id}/session.parquet",
                    ContainerEnvNames.INPUT_FILE.value: \
                        f"./tmp/session/{new_task_id}/input.parquet",
                    ContainerEnvNames.OUTPUT_FILE.value: \
                        f"./tmp/session/{new_task_id}/output.parquet",
                    ContainerEnvNames.CONTAINER_TOKEN.value: "TODO",
                }

                with env_vars(**task_env_vars):
                    result = method_fn(**arguments, **mocked_kwargs)

                last_result_id = len(self.parent.network.server.results) + 1
                if action == AlgorithmStepType.DATA_EXTRACTION.value:
                    for node in self.parent.network.nodes:
                        node.dataframes["my_dataframe"] = result.to_pandas()
                        self.parent.network.server.results.append(
                            {
                                "id": last_result_id,
                                "result": json.dumps({"msg": "OK"}), # TODO
                                "run": {
                                    "id": last_result_id,
                                    "link": f"/api/run/{last_result_id}",
                                    "methods": ["GET", "PATCH"],
                                },
                                "task": {
                                    "id": new_task_id,
                                    "link": f"/api/task/{new_task_id}",
                                    "methods": ["GET", "PATCH"],
                                },
                            }
                        )
                else:
                    self.parent.network.server.results.append(
                        {
                            "id": last_result_id,
                            "result": json.dumps(result),
                            "run": {
                                "id": last_result_id,
                                "link": f"/api/run/{last_result_id}",
                                "methods": ["GET", "PATCH"],
                            },
                            "task": {
                                "id": new_task_id,
                                "link": f"/api/task/{new_task_id}",
                                "methods": ["GET", "PATCH"],
                            },
                        }
                    )
                self.parent.network.server.runs.append(
                    {
                        "id": last_result_id,
                        "started_at": datetime.now().isoformat(),
                        "assigned_at": datetime.now().isoformat(),
                        "finished_at": datetime.now().isoformat(),
                        "log": "mock_log",
                        "ports": [],
                        "status": "completed",
                        "arguments": json.dumps(arguments),
                        "results": {
                            "id": last_result_id,
                            "link": f"/api/result/{last_result_id}",
                            "methods": ["GET", "PATCH"],
                        },
                        "node": {
                            "id": org_id,
                            "name": "mock_node",
                            "status": AuthStatus.ONLINE.value,
                        },
                        "organization": {
                            "id": org_id,
                            "link": f"/api/organization/{org_id}",
                            "methods": ["GET", "PATCH"],
                        },
                        "task": {
                            "id": new_task_id,
                            "link": f"/api/task/{new_task_id}",
                            "methods": ["GET", "PATCH"],
                        },
                    }
                )

            col_id = self.parent.network.server.collaboration_id
            task = {
                "id": new_task_id,
                "runs": f"/api/run?task_id={new_task_id}",
                "results": f"/api/results?task_id={new_task_id}",
                "status": "completed",
                "name": name,
                "databases": ["mock"],
                "description": description,
                "image": "mock_image",
                "init_user": {
                    "id": 1,
                    "link": "/api/user/1",
                    "methods": ["GET", "DELETE", "PATCH"],
                },
                "init_org": {
                    "id": self.parent.organization_id,
                    "link": f"/api/organization/{self.parent.organization_id}",
                    "methods": ["GET", "PATCH"],
                },
                "parent": None,
                "collaboration": {
                    "id": col_id,
                    "link": f"/api/collaboration/{col_id}",
                    "methods": ["DELETE", "PATCH", "GET"],
                },
                "job_id": 1,
                "children": None,
            }
            self.parent.network.server.tasks.append(task)
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

        def create(self, label: str, method: str, arguments: dict, **kwargs) -> dict:
            return self.parent.Task.create(
                self,
                organizations=self.parent.network.organization_ids,
                method=method,
                arguments=arguments,
                action=AlgorithmStepType.DATA_EXTRACTION.value,
            )


class MockAlgorithmClient(MockBaseClient):
    def __init__(self, network: "MockNetwork", *args, **kwargs):
        super().__init__(network, *args, **kwargs)
        self.network = network
