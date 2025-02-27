"""
Development script to populate the server

The `devspace` commands use this script to populate the server with basic
fixtures.
"""

import argparse

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from vantage6.cli.globals import PACKAGE_FOLDER, APPNAME
from vantage6.client import Client


dev_dir = Path("dev") / ".data"
dev_dir.mkdir(exist_ok=True)

client = Client("http://localhost", 7601, "/server", log_level="error")
client.authenticate("root", "root")

parser = argparse.ArgumentParser(
    description="Load basic fixtures for a given number of nodes"
)
parser.add_argument(
    "--number-of-nodes", type=int, default=2, help="Number of nodes to create"
)
args = parser.parse_args()

number_of_nodes = args.number_of_nodes


def create_organization(index):
    name = f"org_{index}"
    if org := next(iter(client.organization.list(name=name)["data"]), None):
        print(f"==> organization `{name}` already exists")
        return org
    else:
        print(f"==> Creating `{name}`")
        org = client.organization.create(
            name=name,
            address1=f"address 1 {index}",
            address2=f"address 2 {index}",
            zipcode=f"1234AB {index}",
            country="NL",
            domain=f"org{index}.org",
        )
        return org


def create_user(index, organization):
    username = f"user_{index}"
    if user := next(iter(client.user.list(username=username)["data"]), None):
        print(f"==> user `{username}` already exists")
        return user
    else:
        print(f"==> Creating `{username}`")
        user = client.user.create(
            username=username,
            firstname=f"user {index}",
            lastname=f"one {index}",
            password="Password123!",
            email=f"user_{index}@one.org",
            organization=organization["id"],
            roles=[1],  # TODO assign proper roles
        )
        print(f"===> Password for `{username}` is `Password123!`")
        return user


def create_node(index, collaboration, organization):
    name = f"node_{index}"
    if next(iter(client.node.list(name=name)["data"]), None):
        print(f"==> node `{name}` already exists")
        return

    print(f"==> Creating node `{name}`")
    print("===> Registering node at the server")
    try:
        node = client.node.create(
            collaboration=collaboration["id"],
            organization=organization["id"],
            name=name,
        )

        print("===> Generating node configuration")
        environment = Environment(
            loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True,
        )
        template = environment.get_template("node_config.j2")

        node_config = template.render(
            {
                "api_key": node["api_key"],  # Use the API key from node creation
                "databases": {"default": "/app/databases/default.csv"},
                "logging": {"file": f"node_{index}.log"},  # Use index in log file name
                "port": 80,
                "server_url": "http://vantage6-server-vantage6-server-service",
                "task_dir": "/tasks",
                "api_path": "/server",
                # TODO user defined config
            }
        )
        config_file = (
            dev_dir / f"node_org_{index}.yaml"
        )  # Use index in config file name
        with open(config_file, "w") as f:
            f.write(node_config)

        print(f"===> Node configuration saved to `{config_file.name}`")
    except Exception as e:
        print(f"Error creating node {name}: {str(e)}")


print("=> creating organizations")
organizations = []
for i in range(number_of_nodes):
    organizations.append(create_organization(i))


print("=> Creating users")
users = []
for i in range(number_of_nodes):
    users.append(create_user(i, organizations[i]))

print("=> Creating collaboration")

if col_1 := next(
    iter(client.collaboration.list(scope="global", name="collab 1")["data"]), None
):
    print("==> `collab 1` already exists")
else:
    print("==> Creating `collab 1`")
    col_1 = client.collaboration.create(
        name="collab 1",
        organizations=[org["id"] for org in organizations],
        encrypted=False,
    )

print("=> Creating nodes")
for i in range(number_of_nodes):
    create_node(i, col_1, organizations[i])
