import pandas
import pickle

from importlib import import_module


class ClientMockProtocol:

    def __init__(self, datasets, module):
        """
        """
        self.n = len(datasets)
        self.datasets = []
        for dataset in datasets:
            self.datasets.append(
                pandas.read_csv(dataset)
            )

        self.lib = import_module(module)
        self.tasks = []

    def create_new_task(self, input_, organization_ids=[]):
        """
        """

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

    def get_task(self, task_id):
        return self.tasks[task_id]

    def get_results(self, task_id):
        """
        """
        task = self.tasks[task_id]
        results = []
        for result in task.get("results"):
            print(result)
            res = pickle.loads(result.get("result"))
            results.append(res)

        return results

    def get_organizations_in_my_collaboration(self):

        organizations = []
        for i in range(self.n):
            organizations.append({
                "id": i,
                "name": f"mock-{i}",
                "domain": f"mock-{i}.org",
            })
        return organizations
