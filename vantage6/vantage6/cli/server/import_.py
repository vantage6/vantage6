import click
import requests
import yaml

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

    This allows you to create organizations, collaborations, users, tasks, etc. from a
    yaml file. This method expects the server configuration file to be located on the
    same machine as this method is invoked from.

    The FILE_ argument should be a path to a yaml file containing the vantage6 formatted
    data to import. The format is as follows:

    ```yaml
    organizations:
    - name: organization1
      domain: example.com
      address1: 123 Main St
      address2: Apt 4B
      zipcode: 12345
      country: USA
      users:
      - username: user1
        password: Password123!
        organization: organization1
        roles:
          - admin
    collaborations:
    - name: collaboration1
      participants:
      - name: organization1
        api_key: api_key1
      - name: organization2
        api_key: api_key2
      encrypted: true
    ```
    """
    info("Validating server version")
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

    info("Loading and validating import file")
    with open(file, "r") as f:
        import_data = yaml.safe_load(f)
    # TODO: validate import file

    client = UserClient(
        server_url=f"{ctx.config['server']['baseUrl']}{ctx.config['server']['apiPath']}",
        auth_url=ctx.config["ui"]["keycloakPublicUrl"],
        auth_realm=ctx.config["ui"]["keycloakRealm"],
        auth_client=ctx.config["ui"]["keycloakClient"],
        log_level="info",
    )

    info("Authenticate using admin credentials (opens browser for login)")
    client.authenticate()

    # TODO: validate that the user has the correct permissions to import data

    info("Dropping all existing data")
    _drop_all(client)

    info("Collecting root role and rule")
    root_role_id = client.role.list(name="Root", include_root=True)["data"][0]["id"]

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

        info(f"Importing users for organization {org['name']}")
        for user in organization["users"]:
            client.user.create(
                username=user["username"],
                password=user["password"],
                organization=org["id"],
                roles=[root_role_id],
            )

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


def _drop_all(client: UserClient) -> None:
    """
    Drop all existing data from the server.
    """
    while collaborations := client.collaboration.list(scope="global")["data"]:
        for collaboration in collaborations:
            info(f"Deleting collaboration {collaboration['name']}")
            client.collaboration.delete(collaboration["id"], delete_dependents=True)

    # TODO: For some reason, the `delete_dependents` parameter is not working for users,
    # so we delete them here first.
    while users := [u for u in client.user.list()["data"] if u["username"] != "admin"]:
        for user in users:
            info(f"Deleting user {user['username']}")
            client.user.delete(user["id"])

    while orgs := [
        o for o in client.organization.list()["data"] if o["name"] != "root"
    ]:
        for org in orgs:
            info(f"Deleting organization {org['name']}")
            client.organization.delete(org["id"], delete_dependents=True)
