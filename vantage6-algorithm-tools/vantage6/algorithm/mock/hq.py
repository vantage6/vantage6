import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import pandas as pd

from vantage6.common.globals import AuthStatus

if TYPE_CHECKING:
    from vantage6.algorithm.mock.network import MockNetwork


class MockHQ:
    def __init__(self, network: "MockNetwork"):
        """
        Create a mock HQ.

        Typically, you do not need to create a mock HQ manually. Instead, you should
        use the MockNetwork class to create a mock network, which contains a mock HQ.

        Parameters
        ----------
        network : MockNetwork
            The network that the HQ belongs to.
        """
        self.network = network

        # These contain the task, runs, results and dataframes as dictionaries that are
        # the same format as you would get from the HQ responses.
        self.tasks = []
        self.runs = []
        self.results = []
        self.dataframes = []

        # We only consider one collaboration and one session as we are typically mocking
        # the algorithms in a single session
        self.session_id = 1
        self.study_id = 1

    @property
    def study(self) -> dict:
        """
        Get the study.
        """
        return {
            "collaboration": {
                "id": self.network.collaboration_id,
                "link": f"/hq/collaboration/{self.network.collaboration_id}",
                "methods": ["PATCH", "GET", "DELETE"],
            },
            "organizations": f"/hq/organization?study_id={self.study_id}",
            "tasks": f"/hq/task?study_id={self.study_id}",
            "name": "Mock Study",
            "id": self.study_id,
        }

    def save_result(self, result: Any, task_id: int):
        """
        Save a result to the mock HQ.

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
        Save a run to the mock HQ.

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
            "started_at": datetime.now(timezone.utc).isoformat(),
            "assigned_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "log": "mock_log",
            "ports": [],
            "status": "completed",
            "arguments": json.dumps(arguments),
            "blob_storage_used": False,
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
        databases: list[list[dict]] | list[dict],
        init_organization_id: int,
    ) -> dict:
        """
        Save a task to the mock HQ.

        Parameters
        ----------
        name : str
            The name of the task.
        description : str
            The description of the task.
        databases : list[list[dict]] | list[dict]
            The databases used by the task.
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
                "id": self.network.collaboration_id,
                "link": f"/api/collaboration/{self.network.collaboration_id}",
                "methods": ["DELETE", "PATCH", "GET"],
            },
            "job_id": 1,
            "children": None,
        }
        self.tasks.append(task)
        return task

    def get_dataframe(self, id_: int) -> dict:
        """
        Get a dataframe by ID
        """
        for dataframe in self.dataframes:
            if dataframe.get("id") == id_:
                return dataframe
        return {"msg": f"Could not find dataframe with id {id_}"}

    def update_dataframe(self, id_: int, dataframes: list[pd.DataFrame]) -> dict:
        """
        Update a dataframe by ID
        """
        for dataframe in self.dataframes:
            if dataframe.get("id") == id_:
                dataframe["columns"] = [
                    {
                        "name": column,
                        "dtype": df.dtypes[column],
                        "node_id": self.network.organization_ids[idx],
                        "dataframe_id": dataframe["id"],
                    }
                    for idx, df in enumerate(dataframes)
                    for column in df.columns
                ]
                return dataframe
        return {"msg": f"Could not find dataframe with id {id_}"}

    def save_dataframe(
        self, name: str, dataframes: list[pd.DataFrame], source_db_label: str
    ) -> dict:
        dataframe_id = len(self.dataframes) + 1
        dataframe = {
            "id": dataframe_id,
            "name": name,
            "db_label": source_db_label,
            "session_id": self.session_id,
            "session": {
                "id": self.session_id,
                "link": f"/api/session/{self.session_id}",
                "methods": ["GET", "PATCH", "DELETE"],
            },
            "tasks": {"msg": "not implemented in the MockHQ"},
            "last_session_task": {"msg": "not implemented in the MockHQ"},
            "columns": [
                {
                    "name": column,
                    "dtype": df.dtypes[column],
                    "node_id": self.network.organization_ids[idx],
                    "dataframe_id": dataframe_id,
                }
                for idx, df in enumerate(dataframes)
                for column in df.columns
            ],
            "ready": True,
            "organizations_ready": [True for _ in dataframes],
        }
        self.dataframes.append(dataframe)
        return dataframe

    def get_label_for_df_id(self, id_: int) -> str:
        """
        Get the label for a dataframe ID
        """
        for dataframe in self.dataframes:
            if dataframe.get("id") == id_:
                return dataframe.get("db_label")
        return None
