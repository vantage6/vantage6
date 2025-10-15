import click

from vantage6.common import info, warning
from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.remove import execute_remove
from vantage6.cli.context.auth import AuthContext
from vantage6.cli.globals import InfraComponentName
from vantage6.cli.utils_kubernetes import get_core_api_with_ssl_handling


@click.command()
@click_insert_context(
    type_=InstanceType.AUTH, include_name=True, include_system_folders=True
)
@click.option("-f", "--force", "force", flag_value=True)
def cli_auth_remove(
    ctx: AuthContext, name: str, system_folders: bool, force: bool
) -> None:
    """
    Function to remove a server.

    Parameters
    ----------
    ctx : ServerContext
        Server context object
    name : str
        Name of the auth server
    system_folders : bool
        Whether to use system folders or user folders
    force : bool
        Whether to ask for confirmation before removing or not
    """
    auth_remove(ctx, name, system_folders, force)


# this new function is just here so that it can be called from the sandbox remove
# command
def auth_remove(ctx: AuthContext, name: str, system_folders: bool, force: bool) -> None:
    # Best-effort cleanup of Keycloak PVCs and their bound PVs after uninstall
    try:
        cleanup_auth_volumes(ctx)
    except Exception as e:
        # Cleanup is best-effort; do not fail the remove command if cleanup fails
        warning(f"Failed to cleanup auth volumes: {e}")

    execute_remove(
        ctx, InstanceType.AUTH, InfraComponentName.AUTH, name, system_folders, force
    )


def cleanup_auth_volumes(ctx: AuthContext) -> None:
    core_api = get_core_api_with_ssl_handling()

    # Label used by the auth chart to tag its resources
    label_selector = f"app.kubernetes.io/instance={ctx.helm_release_name}"

    # Collect PVCs across all namespaces that belong to this release
    pvcs = core_api.list_persistent_volume_claim_for_all_namespaces(
        label_selector=label_selector
    ).items

    # Track PV names bound to these PVCs
    pv_names = {
        pvc.spec.volume_name for pvc in pvcs if pvc.spec and pvc.spec.volume_name
    }

    # Delete PVCs first (namespaced)
    for pvc in pvcs:
        ns = pvc.metadata.namespace
        name_ = pvc.metadata.name
        try:
            info(f"Deleting persistent volume claim {name_} in namespace {ns}")
            core_api.delete_namespaced_persistent_volume_claim(name=name_, namespace=ns)
        except Exception as e:
            # Ignore failures; continue attempting other deletions
            warning(
                f"Failed to delete persistent volume claim {name_} in namespace {ns}: "
                f"{e}"
            )

    # Delete PVs that were bound to those PVCs (cluster-scoped)
    for pv_name in pv_names:
        try:
            info(f"Deleting persistent volume: {pv_name}")
            core_api.delete_persistent_volume(name=pv_name)
        except Exception as e:
            warning(f"Failed to delete persistent volume {pv_name}: {e}")
