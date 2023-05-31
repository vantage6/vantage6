import pandas
import pickle

from importlib import import_module


class ClientMockProtocol:
    """
    The ClientMockProtocol is used to test your algorithm locally. It
    mimics the behaviour of the client and its communication with the server.

    Parameters
    ----------
    datasets : list[str]
        A list of paths to the datasets that are used in the algorithm.
    module : str
        The name of the module that contains the algorithm.
    """
    def __init__(self, datasets: list[str], module: str) -> None:
        self.n = len(datasets)
        self.datasets = []
        for dataset in datasets:
            self.datasets.append(
                pandas.read_csv(dataset)
            )

        self.lib = import_module(module)
        self.tasks = []

    # TODO in v4+, don't provide a default value for list? There is no use
    # in calling this function with 0 organizations as the task will never
    # be executed in that case.
    def create_new_task(self, input_: dict,
                        organization_ids: list[int] = None) -> int:
        """
        Create a new task with the MockProtocol and return the task id.

        Parameters
        ----------
        input_ : dict
            The input data that is passed to the algorithm. This should at
            least  contain the key 'method' which is the name of the method
            that should be called. Another often used key is 'master' which
            indicates that this container is a master container. Other keys
            depend on the algorithm.
        organization_ids : list[int], optional
            A list of organization ids that should run the algorithm.

        Returns
        -------
        int
            The id of the task.
        """
        if organization_ids is None:
            organization_ids = []

        # extract method from lib and input
        master = input_.get("master")

        method_name = input_.get("method")
        if master:
            method = getattr(self.lib, method_name)
        else:
            method = getattr(self.lib, f"RPC_{method_name}")

        # get input
        args = input_.get("args", [])
        kwargs = input_.get("kwargs", {})

        # get data for organization
        results = []
        for org_id in organization_ids:
            data = self.datasets[org_id]
            if master:
                result = method(self, data, *args, **kwargs)
            else:
                result = method(data, *args, **kwargs)

            idx = 999  # we dont need this now
            results.append(
                {"id": idx, "result": pickle.dumps(result)}
            )

        id_ = len(self.tasks)
        task = {
            "id": id_,
            "results": results,
            "complete": "true"
        }
        self.tasks.append(task)
        return task

    def get_task(self, task_id: int) -> dict:
        """
        Return the task with the given id.

        Parameters
        ----------
        task_id : int
            The id of the task.

        Returns
        -------
        dict
            The task details.
        """
        return self.tasks[task_id]

    def get_results(self, task_id: int) -> list[dict]:
        """
        Return the results of the task with the given id.

        Parameters
        ----------
        task_id : int
            The id of the task.

        Returns
        -------
        list[dict]
            The results of the task.
        """
        task = self.tasks[task_id]
        results = []
        for result in task.get("results"):
            print(result)
            res = pickle.loads(result.get("result"))
            results.append(res)

        return results

    def get_organizations_in_my_collaboration(self) -> list[dict]:
        """
        Get mocked organizations.

        Returns
        -------
        list[dict]
            A list of mocked organizations.
        """
        organizations = []
        for i in range(self.n):
            organizations.append({
                "id": i,
                "name": f"mock-{i}",
                "domain": f"mock-{i}.org",
            })
        return organizations


# TODO in v4+, rename to ClientMockProtocol?
class MockAlgorithmClient:
    """
    The MockAlgorithmClient is mimics the behaviour of the AlgorithmClient. It
    can be used to mock the behaviour of the AlgorithmClient and its
    communication with the server.

    Parameters
    ----------
    datasets : list[str]
        A list of paths to the datasets that are used in the algorithm.
    module : str
        The name of the module that contains the algorithm.
    """
    # TODO not only read CSVs but also data types
    def __init__(self, datasets: list[str], module: str) -> None:
        self.n = len(datasets)
        self.datasets = []
        for dataset in datasets:
            self.datasets.append(
                pandas.read_csv(dataset)
            )

        self.lib = import_module(module)
        self.tasks = []

        self.task = self.Task(self)

    class SubClient:
        """
        Create sub groups of commands using this SubClient

        Parameters
        ----------
        parent : MockAlgorithmClient
            The parent client
        """
        def __init__(self, parent) -> None:
            self.parent: MockAlgorithmClient = parent

    class Task(SubClient):
        """
        Task subclient for the MockAlgorithmClient
        """
        def create(self, input_: dict, organization_ids: list[int]) -> int:
            """
            Create a new task with the MockProtocol and return the task id.

            Parameters
            ----------
            input_ : dict
                The input data that is passed to the algorithm. This should at
                least  contain the key 'method' which is the name of the method
                that should be called. Another often used key is 'master' which
                indicates that this container is a master container. Other keys
                depend on the algorithm.
            organization_ids : list[int]
                A list of organization ids that should run the algorithm.

            Returns
            -------
            int
                The id of the task.
            """
            if not len(organization_ids):
                raise ValueError(
                    "No organization ids provided. Cannot create a task for "
                    "zero organizations."
                )

            # extract method from lib and input
            # TODO in v4+, there is no master and this should be removed
            master = input_.get("master")

            method_name = input_.get("method")
            if master:
                method = getattr(self.parent.lib, method_name)
            else:
                method = getattr(self.parent.lib, f"RPC_{method_name}")

            # get input
            args = input_.get("args", [])
            kwargs = input_.get("kwargs", {})

            # get data for organization
            results = []
            for org_id in organization_ids:
                data = self.parent.datasets[org_id]
                if master:
                    result = method(self, data, *args, **kwargs)
                else:
                    result = method(data, *args, **kwargs)

                idx = 999  # we dont need this now
                results.append(
                    {"id": idx, "result": pickle.dumps(result)}
                )

            id_ = len(self.parent.tasks)
            task = {
                "id": id_,
                "results": results,
                "complete": "true"
            }
            self.parent.tasks.append(task)
            return task

        def get(self, task_id: int) -> dict:
            """
            Return the task with the given id.

            Parameters
            ----------
            task_id : int
                The id of the task.

            Returns
            -------
            dict
                The task details.
            """
            return self.parent.tasks[task_id]

    class Result(SubClient):
        """
        Result subclient for the MockAlgorithmClient
        """
        def get_by_task_id(self, task_id: int) -> list[dict]:
            """
            Return the results of the task with the given id.

            Parameters
            ----------
            task_id : int
                The id of the task.

            Returns
            -------
            list[dict]
                The results of the task.
            """
            task = self.parent.tasks[task_id]
            results = []
            for result in task.get("results"):
                # TODO in v4+, this is no longer a pickle
                res = pickle.loads(result.get("result"))
                results.append(res)

            return results

    class Organization(SubClient):
        """
        Organization subclient for the MockAlgorithmClient
        """
        def list(self) -> list[dict]:
            """
            Get mocked organizations in the collaboration.

            Returns
            -------
            list[dict]
                A list of mocked organizations in the collaboration.
            """
            organizations = []
            for i in range(self.parent.n):
                organizations.append({
                    "id": i,
                    "name": f"mock-{i}",
                    "domain": f"mock-{i}.org",
                })
            return organizations
