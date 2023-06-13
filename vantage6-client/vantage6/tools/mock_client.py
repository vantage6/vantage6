import pandas
import json

from importlib import import_module

from vantage6.tools import serialization


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
                {"id": idx, "result": serialization.serialize(result)}
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
            res = json.loads(result.get("result"))
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
