import pandas as pd

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def rich_dataframe_schema_table(
    dataframe_metadata: dict, print_table: bool = True
) -> None | Table:
    """
    Print the schema of a data frame in a rich table. The schema includes the
    column name, data type, and the nodes that have this column.

    Parameters
    ----------
    dataframe_metadata : dict
        Metadata of the data frame. The metadata should contain a list of columns.
        This is the output of the vantage6 server dataframe schema.
    print_table : bool, optional
        If True, the table will be printed. If False, the table object will be
        returned. Default is True.

    Returns
    -------
    None | Table
        If print_table is False, the table object will be returned.

    Examples
    --------
    This will print a rich table with the schema of a data frame.

    ```python
    dataframe_metadata = {
        "columns": [
            {
                "name": "column_name",
                "dtype": "int",
                "node_id": 1
            },
        ]
    }
    rich_dataframe_schema_table(dataframe_metadata)
    ```
    """
    columns = dataframe_metadata["columns"]
    if not columns:
        console.print("No columns found in the dataframe.")
        return
    df = pd.DataFrame(columns)

    grouped_df = (
        df.groupby(["name", "dtype"])["node_id"]
        .apply(lambda x: ", ".join(map(str, x)))
        .reset_index()
    )

    table = Table(title="Dataframe Schema")
    table.add_column("Column Name", justify="left", no_wrap=True)
    table.add_column("Data Type", justify="left")
    table.add_column("Nodes", justify="right")

    for _, row in grouped_df.iterrows():
        table.add_row(row["name"], row["dtype"], row["node_id"])

    out = Panel("No columns found in the dataframe.") if table.row_count == 0 else table
    if print_table:
        console.print(out)
    else:
        return out


def rich_session_table(
    session_metadata: dict, print_table: bool = True
) -> None | Table:
    """
    Print a rich table with the metadata of a session. The metadata includes
    the session ID, name, scope, created at, last used at, and ready status.

    Parameters
    ----------
    session_metadata : dict
        Metadata of the session. The metadata should contain a list of sessions.
        This is the output of the vantage6 server session schema.
    print_table : bool, optional
        If True, the table will be printed. If False, the table object will be
        returned. Default is True.

    Returns
    -------
    None | Table
        If print_table is False, the table object will be returned

    Examples
    --------
    This will print a rich table with the metadata of a session.

    ```python
    session_metadata = [
        {
            "id": 1,
            "name": "session_name",
            "scope": "session_scope",
            "created_at": "2021-01-01",
            "last_used_at": "2021-01-02",
            "ready": True
        }
    ]
    rich_session_table(session_metadata)
    ```
    """
    table = Table(title="Sessions")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("scope")
    table.add_column("created_at")
    table.add_column("last_used_at")
    table.add_column("ready")

    if isinstance(session_metadata, dict):
        session_metadata = [session_metadata]

    for session in session_metadata:
        try:
            table.add_row(
                str(session["id"]),
                session["name"],
                session["scope"],
                session["created_at"],
                session["last_used_at"],
                str(session["ready"]),
            )
        except Exception as e:
            table.add_row("Error", "-", "-", "-", "-", "-")
            console.print(
                f"An error occurred while parsing a row in the session table: {e}"
            )

    out = Panel("No sessions found") if table.row_count == 0 else table
    if print_table:
        console.print(out)
    else:
        return out


def rich_dataframe_table(dataframes: dict, print_table: bool = True) -> None | Table:
    """
    Print a rich table with the metadata of a dataframe. The metadata includes
    the dataframe ID, handle, session ID, last session task ID, number of columns,
    and ready status.

    Parameters
    ----------
    dataframes : dict
        Metadata of the dataframe. The metadata should contain a list of dataframes.
        This is the output of the vantage6 server dataframe schema.
    print_table : bool, optional
        If True, the table will be printed. If False, the table object will be
        returned. Default is True.

    Returns
    -------
    None | Table
        If print_table is False, the table object will be returned

    Examples
    --------
    This will print a rich table with the metadata of a dataframe.

    ```python
    dataframes = [
        {
            "id": 1,
            "handle": "dataframe_handle",
            "session": {"id": 1},
            "last_session_task": {"id": 1},
            "columns": [{"name": "column_name", "dtype": "int", "node_id": 1}],
            "ready": True
        }
    ]
    rich_dataframe_table(dataframes)
    ```
    """
    table = Table()
    table.add_column("ID")
    table.add_column("Handle")
    table.add_column("Session ID")
    table.add_column("Last Session Task ID")
    table.add_column("No. Columns")
    table.add_column("Ready")

    if isinstance(dataframes, dict):
        dataframes = [dataframes]

    for dataframe in dataframes:
        try:
            table.add_row(
                str(dataframe["id"]),
                dataframe["handle"],
                str(dataframe["session"]["id"]),
                str(dataframe["last_session_task"]["id"]),
                str(len(dataframe["columns"])),
                str(dataframe["ready"]),
            )
        except Exception as e:
            table.add_row("Error", "-", "-", "-", "-", "-")
            console.print(
                f"An error occurred while parsing a row in the dataframe table: {e}"
            )

    out = Panel("No dataframes found") if table.row_count == 0 else table
    if print_table:
        console.print(out)
    else:
        return out


def rich_task_table(tasks, print_table=True):
    """
    Print a rich table with the metadata of a task. The metadata includes the
    task ID, name, status, type, and dataframe handle.

    Parameters
    ----------
    tasks : dict
        Metadata of the task. The metadata should contain a list of tasks.
        This is the output of the vantage6 server task schema.
    print_table : bool, optional
        If True, the table will be printed. If False, the table object will be
        returned. Default is True.

    Returns
    -------
    None | Table
        If print_table is False, the table object will be returned

    Examples
    --------
    This will print a rich table with the metadata of a task.

    ```python
    tasks = [
        {
            "id": 1,
            "name": "task_name",
            "status": "completed",
            "dataframe": {"handle": "dataframe_handle"}
        }
    ]
    rich_task_table(tasks)
    ```
    """

    def color(status):
        color = "green" if status == "completed" else "yellow"
        return f"[{color}]{status}[/{color}]"

    table = Table(border_style="gray35", header_style="gray35")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("Type")
    table.add_column("Dataframe")

    for task in tasks:
        table.add_row(
            str(task["id"]),
            task["name"],
            color(task["status"]),
            "session-builder" if task["dataframe"] else "compute",
            task["dataframe"]["handle"] if task["dataframe"] else "None",
        )

    out = Panel("No tasks found") if table.row_count == 0 else table
    if print_table:
        console.print(out)
    else:
        return out
