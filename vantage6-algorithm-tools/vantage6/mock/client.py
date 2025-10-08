import json
from typing import TYPE_CHECKING, Any

from vantage6.common.enum import AlgorithmStepType

if TYPE_CHECKING:
    from vantage6.mock.network import MockNetwork

class MockBaseClient:
    def __init__(self, network: "MockNetwork"):
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

            task = self.parent.network.server.save_task(
                init_organization_id=self.parent.organization_id,
                name=name,
                description=description,
                databases=databases,
            )

            # get data for organization
            for org_id in organizations:
                node = self.parent.network.get_node(org_id)

                result = node.simulate_task_run(method, arguments, databases, action)
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

            task = self.parent.network.server.save_task(
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
                result_response = self.parent.network.server.save_result(
                    {}, task["id"]
                )
                self.parent.network.server.save_run(
                    arguments, task["id"], result_response["id"], org_id
                )

            return task


class MockAlgorithmClient(MockBaseClient):
    def __init__(self, network: "MockNetwork", *args, **kwargs):
        super().__init__(network, *args, **kwargs)
        self.network = network
