import json
import traceback
from typing import TYPE_CHECKING, Any

from vantage6.common.enum import AlgorithmStepType

from vantage6.algorithm.tools.exceptions import (
    MethodNotFoundError,
    SessionActionMismatchError,
)
from vantage6.algorithm.tools.util import error, warn

from vantage6.node.k8s.exceptions import DataFrameNotFound

if TYPE_CHECKING:
    from vantage6.mock.network import MockNetwork
    from vantage6.mock.node import MockNode


class MockBaseClient:
    def __init__(self, network: "MockNetwork"):
        self.network = network
        print("0")
        self.task = self.Task(self)
        self.result = self.Result(self)
        self.run = self.Run(self)
        self.organization = self.Organization(self)
        self.collaboration = self.Collaboration(self)
        self.study = self.Study(self)

        # Which organization do I belong to?
        self.organization_id = 0
        # Store missing attributes in a set for __getattr__ to check
        self._missing_attributes = set(
            [
                "_access_token",
                "_ClientBase__auth_url",
                "_ClientBase__check_algorithm_store_valid",
                "_ClientBase__server_url",
                "_decrypt_run_data",
                "_decrypt_field",
                "_download_run_data_from_server",
                "_fetch_and_decrypt_run_data",
                "_multi_page_request",
                "_refresh_token",
                "_refresh_url",
                "_upload_run_data_to_server",
                "auth_url",
                "authenticate",
                "check_if_blob_store_enabled",
                "collaboration_id",
                "cryptor",
                "databases",
                "generate_path_to",
                "headers",
                "image",
                "log",
                "name",
                "node_id",
                "obtain_new_token",
                "request",
                "server_url",
                "session_id",
                "setup_encryption",
                "store_id",
                "study_id",
                "token",
                "wait_for_task_completion",
                "whoami",
            ]
        )

    def __getattr__(self, name: str):
        """Handle access to missing attributes."""
        if hasattr(self, "_missing_attributes") and name in self._missing_attributes:
            warn(f"The attribute {name} is not available in the mock client.")
            return None
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )

    def set_missing_subclients(self, names: list[str]) -> None:
        class MissingSubClient(self.SubClient):
            def __init__(self, parent, name: str):
                super().__init__(parent)
                self._name = name

            def __getattr__(self, item):
                warn(
                    f"The subclient {self._name} and its method {item} are not "
                    "available in the mock client."
                )
                return lambda *args, **kwargs: None

        for name in names:
            self.__setattr__(name, MissingSubClient(self, name))

    def set_missing_attributes(self, names: list[str]) -> None:
        """Add names to the set of missing attributes."""
        if not hasattr(self, "_missing_attributes"):
            self._missing_attributes = set()
        self._missing_attributes.update(names)

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

        def missing_method(self, method: str):
            warn(f"The method {method} is not available in the mock client.")
            return

    def wait_for_results(self, task_id: int, interval: float = 1) -> list:
        """
        Wait for results from a task

        Parameters
        ----------
        task_id : int
            The id of the task.
        interval : float, optional
            The interval in seconds to wait between checks if task is finished.
            Default 1. Unused in the mock client.

        Returns
        -------
        list
            The results of the task.
        """
        return self.result.from_task(task_id)

    class Study(SubClient):
        """ """

        def __init__(self, parent) -> None:
            super().__init__(parent)
            for method in [
                "list",
                "create",
                "update",
                "add_organization",
                "remove_organization",
            ]:
                self.__setattr__(
                    method,
                    lambda *args, _method=method, **kwargs: self.missing_method(
                        _method
                    ),
                )

        def get(self, id_: int) -> dict:
            """
            Get the study data by ID.

            Parameters
            ----------
            id_: int
                ID of the study to retrieve

            Returns
            -------
            dict
                Dictionary containing study data.
            """
            return self.parent.network.server.study

    class Task(SubClient):
        """
        Task subclient for the MockAlgorithmClient
        """

        def __init__(self, parent) -> None:
            super().__init__(parent)
            for method in ["get", "list", "delete", "kill"]:
                self.__setattr__(
                    method,
                    lambda *args, _method=method, **kwargs: self.missing_method(
                        _method
                    ),
                )

        def create(
            self,
            organizations: list[int],
            method: str,
            name: str = "mock",
            description: str = "mock",
            databases: list[list[dict]] | list[dict] | None = None,
            arguments: dict | None = None,
            action: str = AlgorithmStepType.FEDERATED_COMPUTE.value,
            *_args,
            **_kwargs,
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

            task = self.parent.network.server.save_task(
                init_organization_id=self.parent.organization_id,
                name=name,
                description=description,
                databases=databases,
            )

            # get data for organization
            for org_id in organizations:
                node = self.parent.network.get_node(org_id)
                try:
                    result = node.simulate_task_run(
                        method, arguments, databases, action
                    )
                except MethodNotFoundError:
                    error(
                        f"Method {method} not found in the {node.network.module_name} "
                        "module. Did you specify the correct method name? And are you "
                        "sure that the method is available in the top level of your "
                        "algorithm module?"
                    )
                    return
                except SessionActionMismatchError:
                    error(
                        f"The {method} method is not a computation task, are you sure "
                        "you specified the correct method?"
                    )
                    return
                except DataFrameNotFound as e:
                    error(f"A dataframe you specified does not exist: {e}")
                    return
                except Exception as e:
                    error(f"Error simulating task run for organization {org_id}: {e}")
                    traceback.print_exc()
                    return

                result_response = self.parent.network.server.save_result(
                    result, task["id"]
                )
                self.parent.network.server.save_run(
                    arguments, task["id"], result_response["id"], org_id
                )

            return task

    class Run(SubClient):
        """
        Run subclient for the MockBaseClient
        """

        def __init__(self, parent) -> None:
            super().__init__(parent)
            self.__setattr__(
                "list", lambda *args, **kwargs: self.missing_method("list")
            )

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

        def __init__(self, parent) -> None:
            super().__init__(parent)
            for method in ["update", "create", "delete"]:
                self.__setattr__(
                    method,
                    lambda *args, _method=method, **kwargs: self.missing_method(
                        _method
                    ),
                )

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

        def __init__(self, parent) -> None:
            super().__init__(parent)
            for method in [
                "list",
                "create",
                "delete",
                "update",
                "add_organization",
                "remove_organization",
            ]:
                self.__setattr__(
                    method,
                    lambda *args, _method=method, **kwargs: self.missing_method(
                        _method
                    ),
                )

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
        super().__init__(network)
        self.network = network
        self.dataframe = self.Dataframe(self)

        self.set_missing_subclients(
            [
                "util",
                "user",
                "role",
                "node",
                "rule",
                "store",
                "algorithm",
                "session",
            ]
        )

        self.set_missing_attributes(
            [
                "_get_logger",
                "auth_client",
                "auth_realm",
                "authenticate_service_account",
                "initialize_service_account",
                "is_service_account",
                "kc_openid",
                "Node",
                "obtain_new_token_interactive",
                "Role",
                "Rule",
                "service_account_client_name",
                "service_account_client_secret",
                "setup_collaboration",
                "User",
                "Util",
            ]
        )

    class Dataframe(MockBaseClient.SubClient):
        def __init__(self, parent) -> None:
            super().__init__(parent)
            self.__setattr__(
                "delete",
                lambda *args, _method="delete", **kwargs: self.missing_method(_method),
            )

        def get(self, id_: int) -> dict:
            """
            Get dataframe by ID
            """
            for dataframe in self.parent.network.server.dataframes:
                if dataframe.get("id") == id_:
                    return dataframe
            return {"msg": f"Could not find dataframe with id {id_}"}

        def create(
            self,
            label: str,
            method: str,
            arguments: dict | None = None,
            name: str = "mock_dataframe",
            **kwargs,
        ) -> dict:
            if not arguments:
                arguments = {}

            task = self.parent.network.server.save_task(
                init_organization_id=self.parent.organization_id,
                name=name,
                description=f"Mock dataframe creation for {label}",
                databases=[{"label": label}],
            )

            # get data for organization
            dataframes = []
            for org_id in self.parent.network.organization_ids:
                node = self.parent.network.get_node(org_id)

                try:
                    df_response = node.simulate_dataframe_creation(
                        method, arguments, label, name
                    )
                except SessionActionMismatchError:
                    error(f"The function {method} is not a data extraction method.")
                    return
                except Exception as e:
                    error(
                        "Error simulating dataframe creation for organization "
                        f"{org_id}: {e}"
                    )
                    return

                dataframes.append(df_response)

                # In case of a dataframe we do not store a result, as the dataframe
                # creation on the node is the result of this action.
                result_response = self.parent.network.server.save_result({}, task["id"])
                self.parent.network.server.save_run(
                    arguments, task["id"], result_response["id"], org_id
                )

            dataframe = self.parent.network.server.save_dataframe(
                name=name,
                dataframes=dataframes,
                source_db_label=label,
            )

            return dataframe

        def preprocess(
            self, id_: int, image: str, method: str, arguments: dict
        ) -> dict:
            """ """
            dataframe = self.parent.network.server.get_dataframe(id_)
            data_frame_name = dataframe.get("name")
            if not dataframe or not data_frame_name:
                return {"msg": f"An error occurred while fetching dataframe {id_}"}

            task = self.parent.network.server.save_task(
                init_organization_id=self.parent.organization_id,
                name=f"Preprocess {data_frame_name}",
                description=f"Preprocess {data_frame_name}",
                databases=[{"label": data_frame_name}],
            )

            dataframes = []
            for org_id in self.parent.network.organization_ids:
                node = self.parent.network.get_node(org_id)
                try:
                    df = node.simulate_dataframe_preprocessing(
                        data_frame_name, image, method, arguments
                    )
                except SessionActionMismatchError:
                    error(f"The function {method} is not a preprocessing method.")
                    return
                except Exception as e:
                    error(
                        "Error simulating dataframe preprocessing for organization "
                        f"{org_id}: {e}"
                    )
                    return
                dataframes.append(df)

                result_response = self.parent.network.server.save_result({}, task["id"])
                self.parent.network.server.save_run(
                    arguments, task["id"], result_response["id"], org_id
                )

            return self.parent.network.server.update_dataframe(id_, dataframes)

        def list(self) -> list[dict]:
            """
            List all dataframes
            """
            return self.parent.network.server.dataframes


class MockAlgorithmClient(MockBaseClient):
    def __init__(self, node: "MockNode", *args, **kwargs):
        super().__init__(node.network)

        self.image = "mock-image"
        self.node_id = node.id_
        self.collaboration_id = node.collaboration_id
        self.study_id = node.network.server.study_id
        self.organization_id = node.organization_id

        # these need to be set from the call
        self.databases = None

    def set_databases(self, databases: list[list[dict]]):
        """
        Set the databases for the algorithm client.

        Parameters
        ----------
        databases : list[list[dict]]
            The databases to set for the algorithm client.
        """
        self.databases = databases

    class Task(MockBaseClient.Task):
        def create(self, *args, **kwargs):
            """
            Create a new task with the mock algorithm client. This is the algorithm
            client, so the databases need to be set using `set_databases` before
            creating a task.
            """
            if self.parent.databases is None:
                error("Databases need to be set before creating a task")
                return

            # inject the mock data into the arguments
            kwargs["databases"] = self.parent.databases
            return super().create(*args, **kwargs)
