from pathlib import Path

import click
from colorama import Fore, Style

from vantage6.common import (
    bytes_to_base64s,
    debug,
    error,
    info,
    warning,
)
from vantage6.common.encryption import RSACryptor

from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
from vantage6.cli.node.common import create_client_and_authenticate, select_node


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option(
    "-c",
    "--config",
    default=None,
    help="Absolute path to configuration-file; overrides NAME",
)
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Search for configuration in system folders rather than user folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Search for configuration in user folders rather than "
    "system folders. This is the default",
)
@click.option(
    "--no-upload",
    "upload",
    flag_value=False,
    default=True,
    help="Don't upload the public key to the server",
)
@click.option(
    "-o",
    "--organization-name",
    default=None,
    help="Organization name. Used in the filename of the private key"
    " so that it can easily be recognized again later",
)
@click.option(
    "--overwrite",
    "overwrite",
    flag_value=True,
    default=False,
    help="Overwrite existing private key if present",
)
def cli_node_create_private_key(
    name: str,
    config: str,
    system_folders: bool,
    upload: bool,
    organization_name: str | None,
    overwrite: bool,
) -> None:
    """
    Create and upload a new private key

    Use this command with caution! Uploading a new key has several
    consequences, e.g. you and other users of your organization
    will no longer be able to read the results of tasks encrypted with current
    key.
    """
    NodeContext.LOGGING_ENABLED = False
    if config:
        name = Path(config).stem
        ctx = NodeContext(name, system_folders, config)
    else:
        # retrieve context
        name = select_node(name, system_folders)

        # Create node context
        ctx = NodeContext(name, system_folders)

    # Authenticate with the server to obtain organization name if it wasn't
    # provided
    if organization_name is None:
        client = create_client_and_authenticate(ctx)
        organization_name = client.whoami.organization_name

    # create directory where private key goes if it doesn't exist yet
    ctx.type_data_folder(system_folders).mkdir(parents=True, exist_ok=True)

    # generate new key, and save it
    filename = f"privkey_{organization_name}.pem"
    file_ = ctx.type_data_folder(system_folders) / filename

    if file_.exists():
        warning(f"File '{Fore.CYAN}{file_}{Style.RESET_ALL}' exists!")

        if overwrite:
            warning("'--overwrite' specified, so it will be overwritten ...")

    if file_.exists() and not overwrite:
        error("Could not create private key!")
        warning(
            "If you're **sure** you want to create a new key, "
            "please run this command with the '--overwrite' flag"
        )
        warning("Continuing with existing key instead!")
        private_key = RSACryptor(file_).private_key

    else:
        try:
            info("Generating new private key")
            private_key = RSACryptor.create_new_rsa_key(file_)

        except Exception as e:
            error(f"Could not create new private key '{file_}'!?")
            debug(e)
            info("Bailing out ...")
            exit(1)

        warning(f"Private key written to '{file_}'")
        warning(
            "If you're running multiple nodes, be sure to copy the private "
            "key to the appropriate directories!"
        )

    # create public key
    info("Deriving public key")
    public_key = RSACryptor.create_public_key_bytes(private_key)

    # update config file
    info("Updating configuration")
    # TODO v5+ this probably messes up the current config as the template is used...
    # Fix when reimplementing this in v5
    ctx.config["encryption"]["private_key"] = str(file_)
    ctx.config_manager.put(ctx.config)
    ctx.config_manager.save(ctx.config_file)

    # upload key to the server
    if upload:
        info(
            "Uploading public key to the server. "
            "This will overwrite any previously existing key!"
        )

        if "client" not in locals():
            client = create_client_and_authenticate(ctx)

        # TODO what happens if the user doesn't have permission to upload key?
        # Does that lead to an exception or not?
        try:
            client.request(
                f"/organization/{client.whoami.organization_id}",
                method="patch",
                json={"public_key": bytes_to_base64s(public_key)},
            )

        except Exception as e:
            error("Could not upload the public key!")
            debug(e)
            exit(1)
    else:
        warning("Public key not uploaded!")

    info("[Done]")
