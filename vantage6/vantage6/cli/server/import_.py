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
    print(ctx.config)
    response = requests.get(
        f"{ctx.config['server']['baseUrl']}{ctx.config['server']['apiPath']}/version"
    )
    if response.status_code != 200:
        error("Unable to get server version")
        return

    body = response.json()
    if "version" not in body:
        error("Server gave a valid response but did not include the version")
        return

    # Compare it to this package version
    server_version = body["version"]
    if server_version != __version__:
        error(
            f"You are using CLI version {__version__} but the server is running "
            f"version {server_version}. Please use the same version of the CLI and "
            "server."
        )
        return

    info("Validating import file")
    import yaml

    with open(file, "r") as f:
        import_data = yaml.safe_load(f)
    # TODO: validate import file

    # TODO: Call the vantage6 APIs (core and auth?) to import the data
    client = UserClient(
        server_url=f"{ctx.config['server']['baseUrl']}{ctx.config['server']['apiPath']}",
        auth_url=ctx.config["ui"]["keycloakPublicUrl"],
        auth_realm=ctx.config["ui"]["keycloakRealm"],
        auth_client=ctx.config["ui"]["keycloakClient"],
        log_level="info",
    )

    info("Authenticate using admin credentials")
    client.authenticate()

    # TODO: drop all functionality
    info("Dropping all existing data")
    if drop_all:

        while collaborations := client.collaboration.list(scope="global")["data"]:
            for collaboration in collaborations:
                info(f"Deleting collaboration {collaboration['name']}")
                client.collaboration.delete(collaboration["id"], delete_dependents=True)

        print(client.user.list())
        while users := [
            u for u in client.user.list()["data"] if u["username"] != "admin"
        ]:
            for user in users:
                info(f"Deleting user {user['username']}")
                client.user.delete(user["id"])

        while orgs := [
            o for o in client.organization.list()["data"] if o["name"] != "root"
        ]:
            for org in orgs:
                info(f"Deleting organization {org['name']}")
                client.organization.delete(org["id"], delete_dependents=True)

    info("Importing organizations")
    organizations = []
    for organization in import_data["organizations"]:
        org = client.organization.create(
            name=organization["name"],
            address1=organization["address1"],
            address2=organization["address2"] or "",
            zipcode=organization["zipcode"],
            country=organization["country"],
            domain=organization["domain"],
            public_key=organization["public_key"],
        )
        organizations.append(org)

        info("Collecting root role and rule")
        root_role_id = client.role.list(name="Root", include_root=True)["data"][0]["id"]

        info(f"Importing users for organization {org['name']}")
        for user in organization["users"]:
            user = client.user.create(
                username=user["username"],
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
            organizations=organization_ids,
            encrypted=collaboration["encrypted"],
        )

    pass
