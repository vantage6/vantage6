from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.columns import Columns

from vantage6.client import ClientBase
from vantage6.client.filter import post_filtering
from vantage6.client.rich.table import rich_dataframe_table, rich_session_table


class SessionSubClient(ClientBase.SubClient):
    """Sub client for session management."""

    @post_filtering(iterable=False)
    def get(self, id_: int, display: bool = False) -> dict:
        """
        Get a session by its ID

        Parameters
        ----------
        id_ : int
            The ID of the session
        display : bool, optional
            Print the result in a table. By default False.

        Returns
        -------
        dict
            The session details
        """
        session_metadata = self.parent.request(f"session/{id_}")
        if display:
            rich_session_table(session_metadata)

        return session_metadata

    @post_filtering()
    def list(
        self,
        name: str = None,
        user: int = None,
        collaboration: int = None,
        scope: str = None,
        page: int = 1,
        per_page: int = 20,
        sort: str = None,
        display: bool = False,
    ):
        """
        List of sessions

        Parameters
        ----------
        name : str, optional
            Filter sessions by name. By default None.
        user : int, optional
            Filter sessions by user ID. By default None.
        collaboration : int, optional
            Filter sessions by collaboration ID, overrides the ``collaboration_id``
            of the client. In case both are not set, no filtering is applied.
        scope : str, optional
            Filter sessions by scope, possible values are ``global``, ``collaboration``,
            ``organization`` and ``own``. By default None.
        page : int, optional
            Pagination page. By default 1.
        per_page : int, optional
            Number of items on a single page. By default 20.
        sort : str, optional
            Sort the result by this field. Adding a minus sign in front of the field
            will sort in descending order. By default None.
        display : bool, optional
            Print the result in a table. By default False.

        Returns
        -------
        list[dict]
            Containing session information
        """
        session_metadata = self.parent.request(
            "session",
            params={
                "name": name,
                "user_id": user,
                "collaboration_id": collaboration or self.parent.collaboration_id,
                "scope": scope,
                "sort": sort,
                "page": page,
                "per_page": per_page,
            },
        )

        if display:
            rich_session_table(session_metadata["data"])
            console = Console()
            console.print("page", page)

        return session_metadata

    @post_filtering(iterable=False)
    def update(
        self, id_: int, name: str = None, scope: str = None, display: bool = False
    ):
        """
        Modify a session

        This will update the session with the given ID. Only the fields that are
        provided will be updated.

        Parameters
        ----------
        id_ : int
            The ID of the session
        name : str, optional
            The new name of the session. By default None.
        scope : str, optional
            The new scope of the session. Possible values are ``global``,
            ``collaboration``, ``organization`` and ``own``. By default None.
        display : bool, optional
            Print the result in a table. By default False.

        Returns
        -------
        dict
            The updated session
        """
        session_metadata = self.parent.request(
            f"session/{id_}",
            method="patch",
            json={"name": name, "scope": scope},
        )

        if display:
            rich_session_table(session_metadata)

        return session_metadata

    @post_filtering(iterable=False)
    def create(
        self,
        scope: str,
        name: str = None,
        collaboration: int = None,
        study: int = None,
        display: bool = False,
    ):
        """
        Create a new session

        This will create an empty session. The session can be populated with one or
        more dataframes.

        Parameters
        ----------
        name: str, optional
            The name of the session. By default None.
        collaboration: int, optional
            The collaboration ID of the session. In case this is not set, the
            collaboration ID of the client is used. When neither is set, the study ID
            needs to be provided.
        study: int, optional
            The study ID of the session. In case this is set, the dataframes in this
            session will be scoped to the study.
        scope: str
            The scope of the session. Possible values are ``global``, ``collaboration``,
            ``organization`` and ``own``. In case not set, the ``own`` scope is used.
        display: bool, optional
            Print the result in a table. By default False.

        Returns
        -------
        dict
            The created session
        """
        col_id = collaboration or self.parent.collaboration_id
        if not col_id:
            self.parent.log.error("No collaboration ID provided or set in the client.")

        session_metadata = self.parent.request(
            "session",
            method="post",
            json={
                "name": name,
                "collaboration_id": col_id,
                "study_id": study,
                "scope": scope,
            },
        )

        if display:
            rich_session_table(session_metadata)

        return session_metadata

    @post_filtering(iterable=False)
    def delete(self, id_: int, delete_dependents: bool = False):
        """
        Deletes a session

        Parameters
        ----------
        id_ : int
            Id of the session you want to delete
        delete_dependents : bool, optional
            Delete all dependent tasks and dataframes of the session as well. This
            includes tasks dataframes. By default False.
        """
        return self.parent.request(
            f"session/{id_}",
            method="delete",
            params={"delete_dependents": delete_dependents},
        )

    @post_filtering()
    def dataframes(self, id_: int, display: bool = False):
        """
        Get the dataframes of a session

        Parameters
        ----------
        id_ : int
            The ID of the session.
        display : bool, optional
            Print the result in a table. By default False.

        Returns
        -------
        list[dict]
            The dataframes of the session
        """
        dataframes = self.parent.request(f"session/{id_}/dataframe")

        if display:
            rich_dataframe_table(dataframes["data"])

        return dataframes

    def tree(
        self,
        name: str = None,
        user: int = None,
        collaboration: int = None,
        scope: str = None,
        page: int = 1,
        per_page: int = 20,
        sort: str = None,
    ):
        """
        Display a tree of sessions and their dataframes.

        Parameters
        ----------
        name : str, optional
            Filter sessions by name. By default None.
        user : int, optional
            Filter sessions by user ID. By default None.
        collaboration : int, optional
            Filter sessions by collaboration ID, overrides the ``collaboration_id``
            of the client. In case both are not set, no filtering is applied.
        scope : str, optional
            Filter sessions by scope, possible values are ``global``, ``collaboration``,
            ``organization`` and ``own``. By default None.
        page : int, optional
            Pagination page. By default 1.
        per_page : int, optional
            Number of items on a single page. By default 20.
        sort : str, optional
            Sort the result by this field. Adding a minus sign in front of the field
            will sort in descending order. By default None.

        Returns
        -------
        list[dict]
            Containing session information
        """
        session_metadata = self.list(
            name=name,
            user=user,
            collaboration=collaboration,
            scope=scope,
            page=page,
            per_page=per_page,
            sort=sort,
            display=False,
        )

        tree = Tree(Panel("[bold green]Available sessions[/bold green]"))

        console = Console()

        for session in session_metadata["data"]:
            session_base = tree.add(
                f"[bold green]Session{session['id']:─>4} ({session['name']})[/bold green]"
            )
            dataframes = self.dataframes(session["id"])
            session_base.add(
                rich_dataframe_table(dataframes["data"], print_table=False)
            )

        console.print(tree)

    def task_tree(self, session: int | None = None) -> None:

        # TODO FM 02-08-2024: Maybe move this to the task subclient?
        # TODO FM 02-08-2024: This needs to be cleaned

        def color(status):
            color = "green" if status == "completed" else "yellow"
            return f"[{color}]{status}[/{color}]"

        def info_box(header, content):
            return f"[b gray35]{header}[/b gray35]\n[green]{content}"

        def root_task_header(task):
            if task["dataframe"]:
                if task["depends_on"]:
                    type_ = "preprocess"
                else:
                    type_ = "data-extraction"
            else:
                type_ = "compute"

            return [
                info_box("ID", task["id"]),
                info_box("Name", f"{task['name'][:15]}.."),
                info_box("Status", color(task["status"])),
                info_box("Type", type_),
                info_box(
                    "Dataframe",
                    (
                        f"[green]{task['dataframe']['name']}[/green]"
                        if task["dataframe"]
                        else "[gray35]None[/gray35]"
                    ),
                ),
            ]

        session_id = session or self.parent.session_id
        if session_id is None:
            self.parent.log.error("No session ID provided or set in the client.")

        tasks = self.parent.task.list(session=session_id)["data"]
        lookup = {task["id"]: self.parent.task.get(task["id"]) for task in tasks}

        tree = Tree(Panel("[b green]Task dependency tree[/b green]"))
        for task in tasks:
            base = tree.add(
                Panel(
                    Columns(root_task_header(task), expand=True),
                    border_style="white",
                )
            )

            table = Table(border_style="gray35", header_style="gray35")
            table.add_column("ID", style="green")
            table.add_column("Name", style="green")
            table.add_column("Status", style="green")
            table.add_column("Type", style="green")
            table.add_column("Dataframe", style="green")

            for dep_task_id in task["depends_on"]:
                dep_task = lookup[dep_task_id]
                table.add_row(
                    str(dep_task["id"]),
                    dep_task["name"],
                    color(dep_task["status"]),
                    "session-builder" if dep_task["dataframe"] else "compute",
                    (
                        dep_task["dataframe"]["name"]
                        if dep_task["dataframe"]
                        else "None"
                    ),
                )

            if table.rows != []:
                base.add(Panel(table))

        Console().print(tree)
