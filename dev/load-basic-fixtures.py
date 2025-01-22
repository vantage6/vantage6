from vantage6.client import Client
from pathlib import Path


dev_dir = Path("dev") / ".data"
dev_dir.mkdir(exist_ok=True)

client = Client("http://localhost", 7601, "/api", log_level="error")
client.authenticate("root", "root")

print("=> creating organizations")

if org_1 := next(iter(client.organization.list(name="org 1")["data"]), None):
    print("==> `org 1` already exists")
else:
    print("==> Creating `org 1`")
    org_1 = client.organization.create(
        name="org 1",
        address1="address 1",
        address2="address 2",
        zipcode="1234AB",
        country="NL",
        domain="one.org",
    )

if org_2 := next(iter(client.organization.list(name="org 2")["data"]), None):
    print("==> `org 2` already exists")
else:
    print("==> Creating `org 2`")
    org_2 = client.organization.create(
        name="org 2",
        address1="address 1",
        address2="address 2",
        zipcode="1234AB",
        country="NL",
        domain="two.org",
    )

print("=> Creating users")
# TODO assign proper roles
if client.user.list(username="user1")["data"]:
    print("==> `user1` already exists")
else:
    print("==> Creating `user1`")
    user1 = client.user.create(
        username="user1",
        firstname="user",
        lastname="one",
        password="Password123!",
        email="user_1@one.org",
        organization=org_1["id"],
    )

if collab_1 := next(
    iter(client.collaboration.list(scope="global", name="collab 1")["data"]), None
):
    print("==> `collab 1` already exists")
else:
    print("==> Creating `collab 1`")
    collab_1 = client.collaboration.create(
        name="collab 1",
        organizations=[org_1["id"], org_2["id"]],
        encrypted=False,
    )

from vantage6.cli.globals import PACKAGE_FOLDER, APPNAME
from jinja2 import Environment, FileSystemLoader

environment = Environment(
    loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
    trim_blocks=True,
    lstrip_blocks=True,
    autoescape=True,
)
template = environment.get_template("node_config.j2")

if client.node.list(name="node org 1")["data"]:
    print("==> `node org 1` already exists")
else:
    print("==> Registering nodes")
    response_1 = client.node.create(
        collaboration=collab_1["id"], organization=org_1["id"], name="node org 1"
    )
    node_config_1 = template.render(
        {
            "api_key": response_1["api_key"],
            "databases": {"default": "/henk.csv"},
            "logging": {"file": f"node_1.log"},
            "port": 7601,
            "server_url": "http://host.docker.internal",
            "task_dir": "/tasks",
            # TODO user defined config
        }
    )
    with open(dev_dir / "node_org_1.yaml", "w") as f:
        f.write(node_config_1)


if client.node.list(name="node org 2")["data"]:
    print("==> `node org 2` already exists")
else:
    print("==> Registering nodes")
    response_2 = client.node.create(
        collaboration=collab_1["id"], organization=org_2["id"], name="node org 2"
    )
    node_config_2 = template.render(
        {
            "api_key": response_2["api_key"],
            "databases": {"default": "/henk.csv"},
            "logging": {"file": f"node_2.log"},
            "port": 7601,
            "server_url": "http://host.docker.internal",
            "task_dir": "/tasks",
            # TODO user defined config
        }
    )
    with open(dev_dir / "node_org_2.yaml", "w") as f:
        f.write(node_config_2)
