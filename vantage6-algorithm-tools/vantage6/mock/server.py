import json
from datetime import datetime
from typing import Any

from vantage6.common.globals import AuthStatus


class MockServer:
    def __init__(self, collaboration_id: int):
        """
        Create a mock server.

        Typically, you do not need to create a mock server manually. Instead, you should
        use the MockNetwork class to create a mock network.

        Parameters
        ----------
        collaboration_id : int
            The id of the collaboration, used to format the responses.
        """

        # These contain the task, runs and results as dictionaries that are the same
        # format as you would get from the server responses.
        self.tasks = []
        self.runs = []
        self.results = []

        # We only consider one collaboration and one session as we are typically mocking
        # the algorithms in a single session
        self.collaboration_id = collaboration_id
        self.session_id = 1
        self.study_id = 1

    def save_result(self, result: Any, task_id: int):
        """
        Save a result to the mock server.

        Parameters
        ----------
        result : Any
            The result to save.
        task_id : int
            The id of the task.

        Returns
        -------
        dict
            The saved result.
        """
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

    def save_run(
        self, arguments: dict, task_id: int, result_id: int, org_id: int
    ) -> dict:
        """
        Save a run to the mock server.

        Parameters
        ----------
        arguments : dict
            The arguments to save.
        task_id : int
            The id of the task.
        result_id : int
            The id of the result.
        org_id : int
            The id of the organization.

        Returns
        -------
        dict
            The saved run.
        """
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

    def save_task(
        self,
        name: str,
        description: str,
        databases: list[dict[str, str]],
        init_organization_id: int,
    ) -> dict:
        """
        Save a task to the mock server.

        Parameters
        ----------
        name : str
            The name of the task.
        description : str
            The description of the task.
        databases : list[dict[str, str]]
            The required databases for the task. This can either be a source database
            or a dataframe.
        init_organization_id : int
            The id of the organization that created the task.

        Returns
        -------
        dict
            The saved task.
        """
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
