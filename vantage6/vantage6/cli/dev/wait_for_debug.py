import click

from vantage6.cli.utils import wait_debug_dap_ready


@click.command()
@click.option("--host", required=True, type=str, help="Host to connect to.")
@click.option("--port", required=True, type=int, help="Port to connect to.")
@click.option(
    "--timeout", default=90, type=int, show_default=True, help="Maximum time to wait (in seconds)."
)
def wait_for_debug(host: str, port: int, timeout: int) -> None:
    """
    Keeps attempting to connect to the specified host and port, waiting for the
    response to begin with 'Content-Length:'. This serves as a simple and
    (far-from-perfect) indication that the Debug Adapter Protocol (DAP) adapter
    is ready to accept client connections.
    See: https://microsoft.github.io/debug-adapter-protocol/

    Parameters
    ----------
    host : str
        Host where the DAP adapter is excepected to be running.
    port : int
        Port where the DAP adapter is excepected to be running.
    timeout : int
        Maximum time to wait (in seconds) before timing out.

    Exit codes
    ----------
    0:
        True if DAP adapter sems to be ready.
    1:
        Failed to connect to the DAP adapter within the specified timeout.
    """
    success = wait_debug_dap_ready(host, port, timeout)
    if success:
        click.echo(f"Debugger adaaaprter at {host}:{port} seems to be ready.")
        raise click.Context.exit(0)
    else:
        click.echo(f"Failed to connect debugger adapter at {host}:{port} (timeout: {timeout} seconds)")
        raise click.Context.exit(1)

