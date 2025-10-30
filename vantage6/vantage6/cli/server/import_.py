import click
import requests
import yaml
from marshmallow import Schema, ValidationError, fields, post_load

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
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(type_=InstanceType.SERVER, sandbox_param="sandbox")
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
            address1=organization.get("address1", ""),
            address2=organization.get("address2", ""),
            zipcode=str(organization.get("zipcode", "")),
            country=organization.get("country", ""),
            domain=organization.get("domain", ""),
            public_key=organization.get("public_key", ""),
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

    # remove all organizations but keep the root organization
    while orgs := [o for o in client.organization.list()["data"] if o["id"] != 1]:
        for org in orgs:
            info(f"Deleting organization {org['name']}")
            client.organization.delete(org["id"], delete_dependents=True)


class StrOrInt(fields.Field):
    """Field that can be a string or an integer"""

    def _serialize(self, value, attr, obj, **kwargs):
        if isinstance(value, str):
            return value
        elif isinstance(value, int):
            return str(value)
        else:
            raise ValidationError("Value must be a string or an integer")


class UserSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class OrganizationSchema(Schema):
    name = fields.Str(required=True)
    address1 = fields.Str(missing="")
    address2 = fields.Str(missing="")
    zipcode = StrOrInt(missing="")
    country = fields.Str(missing="")
    domain = fields.Str(missing="")
    public_key = fields.Str(missing="")
    users = fields.List(fields.Nested(UserSchema), missing=[])


class ParticipantSchema(Schema):
    name = fields.Str(required=True)


class CollaborationSchema(Schema):
    name = fields.Str(required=True)
    participants = fields.List(fields.Nested(ParticipantSchema), required=True)
    encrypted = fields.Bool(missing=False)


class ImportDataSchema(Schema):
    organizations = fields.List(fields.Nested(OrganizationSchema), missing=[])
    collaborations = fields.List(fields.Nested(CollaborationSchema), missing=[])

    @post_load
    def validate_participants_exist(self, data, **kwargs):
        """Validate that all participants exist in organizations"""
        org_names = {org["name"] for org in data.get("organizations", [])}

        for collaboration in data.get("collaborations", []):
            for participant in collaboration.get("participants", []):
                if participant["name"] not in org_names:
                    raise ValidationError(
                        f"Participant {participant['name']} not found in organizations",
                        field_name="collaborations",
                    )
        return data


def _check_import_file(import_data: dict) -> dict:
    """
    Validate import file using Marshmallow schemas.
    Returns the validated and cleaned data.
    """
    schema = ImportDataSchema()
    try:
        return schema.load(import_data)
    except ValidationError as err:
        # Handle validation errors gracefully
        error(f"Validation error: {err.messages}")
        exit(1)
