import click
import requests
import yaml

from vantage6.common import error, info
from vantage6.common.globals import (
    InstanceType,
)

from vantage6.client import UserClient

from vantage6.cli import __version__
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context.server import ServerContext


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
    Import vantage6 resources into a server instance from a yaml FILE.

    This allows you to create organizations, collaborations, users, tasks, etc. from a
    yaml FILE. This method expects the server configuration file to be located on the
    same machine as this method is invoked from.

    This import assigns the root role to all users, which contains all permissions. So
    use this with caution.

    The FILE argument should be a path to a yaml file containing the vantage6 formatted
    data to import.
    """
    info("Validating server version: ")
    info(f"{ctx.config['server']['baseUrl']}{ctx.config['server']['apiPath']}/version")
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

    _check_import_file(import_data)

    client = UserClient(
        server_url=f"{ctx.config['server']['baseUrl']}{ctx.config['server']['apiPath']}",
        auth_url=ctx.config["ui"]["keycloakPublicUrl"],
        auth_realm=ctx.config["ui"]["keycloakRealm"],
        auth_client=ctx.config["ui"]["keycloakClient"],
        log_level="info",
    )

    info("Authenticate using admin credentials (opens browser for login)")
    client.authenticate()

    # Note: we do not validate that the user has the correct permissions to import data.
    # As the user has access to the `v6 server import` command, they already have
    # access to the server+database.

    if drop_all:
        info("Dropping all existing data")
        _drop_all(client)

    info("Collecting root role and rule")
    root_role_id = client.role.list(name="Root", include_root=True)["data"][0]["id"]

    info("Importing organizations")
    organizations = []
    for organization in import_data["organizations"]:
        org = client.organization.create(
            name=organization["name"],
            address1=organization["address1"] or "",
            address2=organization["address2"] or "",
            zipcode=organization["zipcode"] or "",
            country=organization["country"] or "",
            domain=organization["domain"] or "",
        )
        organizations.append(org)

        info(f"Importing users for organization {org['name']}")
        for user in organization.get("users", []):
            client.user.create(
                username=user["username"],
                password=user["password"],
                organization=org["id"],
                roles=[root_role_id],
            )

    info("Importing collaborations")
    all_nodes = []
    for collaboration in import_data["collaborations"]:
        # Collecting organization ids
        organization_ids = []
        for participant in collaboration["participants"]:
            for org in organizations:
                if org["name"] == participant["name"]:
                    organization_ids.append(org["id"])

        col = client.collaboration.create(
            name=collaboration["name"],
            organizations=organization_ids,
            encrypted=collaboration.get("encrypted", False),
        )

        info("Registering nodes for collaboration")
        for participant in collaboration["participants"]:
            for org in organizations:
                if org["name"] == participant["name"]:
                    node = client.node.create(
                        name=f"{collaboration['name']}-{org['name'].replace(' ', '-')}-node",
                        organization=org["id"],
                        collaboration=col["id"],
                    )
                    all_nodes.append(node)

    return all_nodes


def _drop_all(client: UserClient) -> None:
    """
    Drop all existing data from the server.
    """
    while nodes := client.node.list()["data"]:
        for node in nodes:
            info(f"Deleting node {node['name']}")
            client.node.delete(node["id"])

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


def _check_import_file(import_data: dict) -> None:
    """
    Check if the import file is valid.
    """
    main_level = {
        "organizations": list,
        "collaborations": list,
    }
    _check_content_of_dict(import_data, main_level)

    organization_level = {
        "name": str,
        "address1": str,
        "address2": str,
        "zipcode": str,
        "country": str,
        "domain": str,
        "users": list,
    }
    user_level = {
        "username": str,
        "password": str,
    }
    for organization in import_data.get("organizations", []):
        _check_content_of_dict(organization, organization_level)
        for user in organization["users"]:
            _check_content_of_dict(user, user_level)

    collaboration_level = {
        "name": str,
        "participants": list,
        "encrypted": bool,
    }
    participant_level = {
        "name": str,
    }
    for collaboration in import_data.get("collaborations", []):
        _check_content_of_dict(collaboration, collaboration_level)
        for participant in collaboration["participants"]:
            _check_content_of_dict(participant, participant_level)
            if participant["name"] not in [
                o["name"] for o in import_data["organizations"]
            ]:
                error(f"Participant {participant['name']} not found in organizations")
                exit(1)


def _check_content_of_dict(data: dict, options: dict) -> None:
    for key, value in options.items():
        if key not in data:
            error(f"Import file must contain a '{key}' key")
            exit(1)
        if not isinstance(data[key], value):
            error(f"Import file must contain a '{key}' key with a list of dictionaries")
            exit(1)
