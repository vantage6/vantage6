import click
import requests

from vantage6.common import info, warning, error
from vantage6.common.globals import (
    APPNAME,
    InstanceType,
)

from vantage6.cli import __version__
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context.server import ServerContext
from vantage6.cli.utils import check_config_name_allowed

from vantage6.client import UserClient


# TODO this method has a lot of duplicated code from `start`
@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--drop-all",
    is_flag=True,
    default=False,
    help="Drop all existing data before importing",
)
@click_insert_context(type_=InstanceType.SERVER)
def cli_server_import(ctx: ServerContext, file: str, drop_all: bool) -> None:
    """
    Import vantage6 resources into a server instance.

    This allows you to create organizations, collaborations, users, tasks, etc
    from a yaml file.

    The FILE_ argument should be a path to a yaml file containing the vantage6
    formatted data to import.
    """
    info("Validating server version")
    response = requests.get(f"{ctx.config['server']['url']}/api/version")
    if response.status_code != 200:
        error("Unable to get server version")
        return

    body = response.json()
    if "version" not in body:
        error("Server gave a valid response but did not include the version")
        return

    # Compare it to this package version
    if server_version != __version__:
        error(
            f"You are using CLI version {__version__} but the server is running "
            f"version {server_version}. Please use the same version of the CLI and "
            "server."
        )
        return

    info("Validating import file")
    with open(file, "r") as f:
        import_data = yaml.safe_load(f)
    # TODO: validate import file

    # TODO: Call the vantage6 APIs (core and auth?) to import the data
    client = UserClient(
        server_url=ctx.config["server"]["url"],
        uth_url=ctx.config["server"]["keycloakUrl"],
        auth_realm=ctx.config["server"]["keycloakRealm"],
        auth_client=ctx.config["server"]["keycloakClient"],
        log_level="info",
    )

    info("Authenticate using admin credentials")
    client.authenticate()

    info("Importing organizations")
    organizations = []
    for organization in import_data["organizations"]:
        org = client.organization.create(
            name=organization["name"],
            address1=organization["address1"],
            address2=organization["address2"],
            zipcode=organization["zipcode"],
            country=organization["country"],
            domain=organization["domain"],
            public_key=organization["public_key"],
        )
        organizations.append(org)

        info("Collecting root role and rule")
        root_role_id = client.role.list(name="Root")[0]["id"]

        info(f"Importing users for organization {org['name']}")
        for user in organization["users"]:
            user = client.user.create(
                username=user["username"],
                firstname=user["firstname"],
                lastname=user["lastname"],
                password=user["password"],
                organization=org["id"],
                roles=[root_role_id],
            )
            users.append(user)

    info("Importing collaborations")
    for collaboration in import_data["collaborations"]:

        # Collecting organization ids
        organization_ids = []
        for participant in collaboration["participants"]:
            for org in organizations:
                if org["name"] == participant["name"]:
                    organization_ids.append(org["id"])

        collaboration = client.collaboration.create(
            name=collaboration["name"],
            organization_ids=organization_ids,
            encrypted=collaboration["encrypted"],
        )

    pass
