import json

from typing import Any
from rich.console import Console
from rich.table import Table

from vantage6.client import UserClient
from vantage6.common import info, debug
from vantage6.cli.globals import DIAGNOSTICS_IMAGE


class DiagnosticRunner:
    """
    Class to run the diagnostic algorithm on a vantage6 network.

    This class will create a task in the requested collaboration that will test
    the functionality of vantage6, and will report back the results.

    Parameters
    ----------
    client : UserClient
        The client to use for communication with the server.
    collaboration_id : int
        The ID of the collaboration to run the diagnostics in.
    organizations : list[int] | None
        The ID(s) of the organization(s) to run the diagnostics for. If None
        (default), run the diagnostics for all organizations in the
        collaboration.
    online_only : bool
        Whether to run the diagnostics only on nodes that are online. By
        default False
    """

    def __init__(
        self,
        client: UserClient,
        collaboration_id: int,
        organizations: list[int] | None = None,
        online_only: bool = False,
    ) -> None:
        self.client = client
        self.collaboration_id = collaboration_id

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

        info(f"Running diagnostics to {len(self.organization_ids)} " "organization(s)")
        info(f"  organizations: {self.organization_ids}")
        info(f"  collaboration: {self.collaboration_id}")

    def __call__(self, base: bool = True, vpn: bool = True) -> Any:
        """
        Run the diagnostics.

        Parameters
        ----------
        base: bool
            Whether to run the base features of the diagnostic algorithm. By
            default True.
        vpn: bool
            Whether to run the VPN features of the diagnostic algorithm. By
            default True.
        """
        base_results = self.base_features() if base else []
        vpn_results = self.vpn_features() if vpn else []
        return base_results + vpn_results

    def base_features(self) -> list[dict]:
        """
        Create a task to run the base features of the diagnostic algorithm.

        Returns
        -------
        list[dict]
            The results of the diagnostic algorithm.
        """
        task = self.client.task.create(
            collaboration=self.collaboration_id,
            name="test",
            description="Basic Diagnostic test",
            image=DIAGNOSTICS_IMAGE,
            method="base_features",
            organizations=self.organization_ids,
            databases=[{"label": "default"}],
        )
        debug(task)

        return self._wait_and_display(task.get("id"))

    def vpn_features(self) -> list[dict]:
        """
        Create a task to run the VPN features of the diagnostic algorithm.

        Returns
        -------
        list[dict]
            The results of the diagnostic algorithm.
        """
        self.client.node.list(collaboration=self.collaboration_id)

        task = self.client.task.create(
            collaboration=self.collaboration_id,
            name="test",
            description="VPN Diagnostic test",
            image=DIAGNOSTICS_IMAGE,
            method="vpn_features",
            arguments={
                "other_nodes": self.organization_ids,
            },
            organizations=self.organization_ids,
        )

        return self._wait_and_display(task.get("id"))

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
