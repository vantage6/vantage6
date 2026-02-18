import json
from typing import Any

from rich.console import Console
from rich.table import Table

from vantage6.common import debug, info
from vantage6.common.enum import AlgorithmStepType, TaskDatabaseType

from vantage6.client import UserClient

from vantage6.cli.globals import DIAGNOSTICS_IMAGE


class DiagnosticRunner:
    """
    Class to run the diagnostic algorithm on a vantage6 network.

    This class will create a task in the requested collaboration that will test
    the functionality of vantage6, and will report back the results.

    Parameters
    ----------
    client : UserClient
        The client to use for communication with the vantage6 hub.
    collaboration_id : int
        The ID of the collaboration to run the diagnostics in.
    organizations : list[int] | None
        The ID(s) of the organization(s) to run the diagnostics for. If None
        (default), run the diagnostics for all organizations in the
        collaboration.
    online_only : bool
        Whether to run the diagnostics only on nodes that are online. By
        default False
    session_id : int
        The ID of the session to use for the diagnostic test. By default 1.
    database_label : str
        The label of the database to use for the diagnostic test. By default "default".
    """

    def __init__(
        self,
        client: UserClient,
        collaboration_id: int,
        organizations: list[int] | None = None,
        online_only: bool = False,
        session_id: int = 1,
        database_label: str = "olympic-athletes",
    ) -> None:
        self.client = client
        self.collaboration_id = collaboration_id
        self.session_id = session_id
        self.database_label = database_label
        self.extract_task_details = None

        if not organizations:
            # run on all organizations in the collaboration
            # TODO use pagination properly, instead of just getting the first
            # 1000 organizations (which very likely is enough though)
            orgs = self.client.organization.list(
                collaboration=self.collaboration_id, per_page=1000
            )
            self.organization_ids = [org["id"] for org in orgs["data"]]
        else:
            self.organization_ids = organizations

        if online_only:
            nodes = self.client.node.list(
                collaboration=self.collaboration_id, is_online=True
            )
            debug(nodes)
            online_orgs = [node["organization"]["id"] for node in nodes["data"]]
            self.organization_ids = list(
                set(self.organization_ids).intersection(online_orgs)
            )

        info(f"Running diagnostics to {len(self.organization_ids)} organization(s)")
        info(f"  organizations: {self.organization_ids}")
        info(f"  collaboration: {self.collaboration_id}")

    def __call__(self) -> Any:
        """
        Run the diagnostics.

        Parameters
        ----------
        base: bool
            Whether to run the base features of the diagnostic algorithm. By
            default True.
        """
        # first create extraction task
        if not self.extract_task_details:
            self.extract()
        # then create base features task
        base_results = self.base_features()
        return base_results

    def base_features(self) -> list[dict]:
        """
        Create a task to run the base features of the diagnostic algorithm.

        Returns
        -------
        list[dict]
            The results of the diagnostic algorithm.
        """
        info("Starting task to test base features...")
        task = self.client.task.create(
            collaboration=self.collaboration_id,
            name="test",
            description="Basic Diagnostic test",
            image=DIAGNOSTICS_IMAGE,
            method="base_features",
            organizations=self.organization_ids,
            databases=[
                {
                    "dataframe_id": self.extraction_task_details.get("id"),
                    "type": TaskDatabaseType.DATAFRAME,
                }
            ],
            session=self.session_id,
            action=AlgorithmStepType.CENTRAL_COMPUTE,
        )
        debug(task)

        return self._wait_and_display(task.get("id"))

    def extract(self) -> None:
        """
        Create a task to extract the database.
        """
        info("Before running compute task, we need to create a dataframe")
        info(f"Creating dataframe for database with label: {self.database_label}")
        self.extraction_task_details = self.client.dataframe.create(
            label=self.database_label,
            image=DIAGNOSTICS_IMAGE,
            method="read_csv",
            arguments={},
            session=self.session_id,
        )

        self.client.wait_for_results(
            self.extraction_task_details.get("last_session_task", {}).get("id")
        )
        info("Dataframe created successfully!")

    def _wait_and_display(self, task_id: int) -> list[dict]:
        """
        Wait for the task to finish and then display the results.

        Parameters
        ----------
        task_id : int
            The ID of the task to wait for.

        Returns
        -------
        list[dict]
            The results of the diagnostic algorithm.
        """
        # TODO should we have the option to combine these in one request? Seems
        # like it would be more efficient
        # TODO ensure that we get all pages of results
        results = self.client.wait_for_results(task_id=task_id)["data"]
        runs = self.client.run.from_task(task_id=task_id)["data"]
        print("\n")
        for res in results:
            matched_run = [run for run in runs if run["id"] == res["run"]["id"]][0]
            self.display_diagnostic_results(res, matched_run["organization"]["id"])
            print()
        return results

    def display_diagnostic_results(self, result: dict, org_id: int) -> None:
        """
        Print the results of the diagnostic algorithm.

        Parameters
        ----------
        result : list[dict]
            The result of the diagnostic algorithm.
        org_id : int
            The ID of the organization that the diagnostic algorithm was run on
        """
        res = json.loads(result["result"])
        t_ = Table(title=f"Basic Diagnostics Summary (organization {org_id})")
        t_.add_column("name")
        t_.add_column("success")
        e_ = Table(title=f"Basic Diagnostics Errors (organization {org_id})")
        e_.add_column("name")
        e_.add_column("exception")
        e_.add_column("traceback")
        e_.add_column("payload")
        errors = False
        for diag in res:
            if diag["success"]:
                success = ":heavy_check_mark: [green]success[/green]"
            else:
                success = ":x: [red]failed[/red]"
                e_.add_row(
                    diag["name"], diag["exception"], diag["traceback"], diag["payload"]
                )
                errors = True
            t_.add_row(diag["name"], success)

        console = Console()
        console.print(t_)
        if errors:
            console.print(e_)
