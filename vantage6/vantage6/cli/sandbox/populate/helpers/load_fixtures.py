"""
Development script to populate the server
"""

import traceback
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from vantage6.client import Client

from vantage6.cli.globals import APPNAME, PACKAGE_FOLDER
from vantage6.cli.sandbox.populate.helpers.utils import (
    NodeConfigCreationDetails,
    replace_wsl_path,
)


def clear_dev_folder(dev_dir: Path, name: str) -> None:
    node_dev_dir = dev_dir / name
    if node_dev_dir.exists():
        for file_ in node_dev_dir.iterdir():
            file_.unlink()
        node_dev_dir.rmdir()
        print(f"===> Dev folder for node `{name}` cleared")


def create_organizations(
    client: Client, number_of_nodes: int
) -> tuple[list[dict], dict]:
    """
    Create organizations. If the organization already exists, it is added to the
    existing organizations list. If the organization is the root organization, it is
    patched so that the admin user is also in the organization.

    Returns
    -------
    tuple[list[dict], dict]
        A tuple containing the list of organizations and the creation details.
    """
    organizations = []
    creation_details = {
        "created": [],
        "existing": [],
        "root_org_patched": [],
    }

    existing_organizations = client.organization.list()["data"]
    for i in range(1, number_of_nodes + 1):
        name = f"org_{i}"
        if org := next(
            iter([org for org in existing_organizations if org["name"] == name]), None
        ):
            creation_details["existing"].append({"name": name, "domain": org["domain"]})
            organizations.append(org)
        elif i == 1:
            # Patch the root organization so that admin user is also in the org
            org = client.organization.update(
                id_=1,
                name=name,
            )
            creation_details["root_org_patched"].append(
                {"name": name, "domain": org["domain"]}
            )
            organizations.append(org)
        else:
            org = client.organization.create(
                name=name,
                address1=f"First address line {i}",
                address2=f"Second address line {i}",
                zipcode="1234AB",
                country="Earthland",
                domain=f"org{i}.org",
            )
            creation_details["created"].append({"name": name, "domain": org["domain"]})
            organizations.append(org)

    return organizations, creation_details


def create_collaborations(
    client: Client, organizations: list[dict]
) -> tuple[list[dict], dict]:
    """
    Create collaborations. If the collaboration already exists, it is added to the
    existing collaborations list.

    Returns
    -------
    tuple[dict, dict]
        A tuple containing the collaboration and the creation details.
    """
    creation_details = {"created": [], "existing": []}
    collab_name = "demo"
    existing_collaborations = client.collaboration.list(
        scope="global", name=collab_name
    )["data"]
    if collab := next(iter(existing_collaborations), None):
        creation_details["existing"].append({"name": collab_name, "id": collab["id"]})
    else:
        collab = client.collaboration.create(
            name=collab_name,
            organizations=[org["id"] for org in organizations],
            encrypted=False,
        )
        creation_details["created"].append({"name": collab_name, "id": collab["id"]})
    return collab, creation_details


def create_users(client: Client, organizations: list[dict]) -> dict:
    """
    Create users. If the user already exists, it is added to the existing users list.

    Returns
    -------
    dict
        The creation details.
    """
    creation_details = {"created": [], "existing": []}
    existing_users = client.user.list()["data"]
    for index, org in enumerate(organizations):
        username = f"user_{index + 1}"
        if next(
            iter([user for user in existing_users if user["username"] == username]),
            None,
        ):
            creation_details["existing"].append(
                {
                    "username": username,
                    "organization": org["name"],
                }
            )
        else:
            password = "Password123!"
            client.user.create(
                username=username,
                password=password,
                organization=org["id"],
                roles=[1],  # TODO assign proper roles
            )
            creation_details["created"].append(
                {
                    "username": username,
                    "password": password,
                    "organization": org["name"],
                }
            )
    return creation_details


def register_node(
    client: Client,
    node_name: str,
    collaboration: dict,
    organization: dict,
) -> dict:
    """
    Register a node at the server.

    Returns
    -------
    dict
        The node registration details.
    """
    return client.node.create(
        collaboration=collaboration["id"],
        organization=organization["id"],
        name=node_name,
    )


def create_node_config(
    node_number: int,
    node_name: str,
    dev_dir: Path,
    task_directory: str,
    task_namespace: str,
    node_starting_port_number: int,
    organization: dict,
    node: dict,
) -> dict:
    """
    Create a node configuration file.

    Returns
    -------
    dict
        The node configuration details.
    """
    # Create a folder for all config files for a single node
    node_dev_dir = dev_dir / node_name
    node_dev_dir.mkdir(exist_ok=True)

    # Generate node configuration
    environment = Environment(
        loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
    )
    template = environment.get_template("node_config_nonk8s.j2")

    node_config = template.render(
        {
            "logging": {"file": f"node_{node_number}.log"},
            "port": 7601,
            "server_url": "http://vantage6-server-vantage6-server-service",
            "task_dir": f"{task_directory}/node_{node_number}",
            "task_dir_extension": f"node_{node_number}",
            "api_path": "/server",
            "task_namespace": task_namespace,
            "node_proxy_port": node_starting_port_number + (node_number - 1),
        }
    )
    config_file = node_dev_dir / f"node_org_{node_number}.yaml"
    with open(config_file, "w") as f:
        f.write(node_config)

    # also make sure the task directory exists
    task_dir = Path(f"{task_directory}/node_{node_number}")
    task_dir = replace_wsl_path(task_dir)
    task_dir.mkdir(parents=True, exist_ok=True)

    # Create .env file for the node
    env_file = node_dev_dir / ".env"
    with open(env_file, "w") as f:
        f.write(f"V6_API_KEY={node['api_key']}\n")
        f.write(f"V6_NODE_NAME={node_name}\n")

    return {
        "name": f"node-{node_number}",
        "organization": organization["name"],
        "api_key": node["api_key"],
        "config_file": str(config_file),
        "env_file": str(env_file),
    }


def create_session(client: Client, collaboration: dict) -> dict:
    """
    Create a session.

    Returns
    -------
    dict
        The session creation details.
    """
    session = client.session.create(
        collaboration=collaboration["id"],
        name="session (collaboration scope)",
        scope="collaboration",
    )
    creation_details = {
        "created": [
            {
                "name": "session (collaboration scope)",
                "id": session["id"],
            }
        ],
    }
    return creation_details


def print_creation_details(creation_details: dict) -> str:
    """
    Print the creation details.

    Returns
    -------
    str
        The creation summary.
    """
    summary = "=== Creation Summary ===\n"

    summary += f"\nOrganizations: {len(creation_details['organizations']['created'])} "
    summary += f"created, {len(creation_details['organizations']['existing'])} existing"
    summary += f", {len(creation_details['organizations']['root_org_patched'])} root "
    summary += "org patched"
    if creation_details["organizations"]["created"]:
        summary += "\n  Created:"
        for org in creation_details["organizations"]["created"]:
            summary += f"\n    - {org['name']} ({org['domain']})"
    if creation_details["organizations"]["existing"]:
        summary += "\n  Existing:"
        for org in creation_details["organizations"]["existing"]:
            summary += f"\n    - {org['name']} ({org['domain']})"
    if creation_details["organizations"]["root_org_patched"]:
        summary += "\n  Root org patched:"
        for org in creation_details["organizations"]["root_org_patched"]:
            summary += f"\n    - {org['name']} ({org['domain']})"

    summary += f"\n\nUsers: {len(creation_details['users']['created'])} created, "
    summary += f"{len(creation_details['users']['existing'])} existing"
    if creation_details["users"]["created"]:
        summary += "\n  Created:"
        for user in creation_details["users"]["created"]:
            summary += f"\n    - {user['username']} - Password: "
            summary += f"{user['password']} - Org: {user['organization']}"
    if creation_details["users"]["existing"]:
        summary += "\n  Existing:"
        for user in creation_details["users"]["existing"]:
            summary += f"\n    - {user['username']} - Org: "
            summary += f"{user['organization']}"

    summary += f"\n\nNodes: {len(creation_details['nodes']['created'])} created, "
    summary += f"{len(creation_details['nodes']['existing'])} existing"
    if creation_details["nodes"]["created"]:
        summary += "\n  Created:"
        for node in creation_details["nodes"]["created"]:
            summary += f"\n    - {node['name']} (Org: {node['organization']})"
            summary += f"\n      API Key: {node['api_key']}"
            if "config_file" in node:
                summary += f"\n      Config: {node['config_file']}"
            if "env_file" in node:
                summary += f"\n      Env: {node['env_file']}"
    if creation_details["nodes"]["existing"]:
        summary += "\n  Existing:"
        for node in creation_details["nodes"]["existing"]:
            summary += f"\n    - {node['name']} (Org: {node['organization']})"

    summary += (
        f"\n\nCollaborations: {len(creation_details['collaborations']['created'])} "
    )
    summary += (
        f"created, {len(creation_details['collaborations']['existing'])} existing"
    )
    if creation_details["collaborations"]["created"]:
        summary += "\n  Created:"
        for collab in creation_details["collaborations"]["created"]:
            summary += f"\n    - {collab['name']} (ID: {collab['id']})"
    if creation_details["collaborations"]["existing"]:
        summary += "\n  Existing:"
        for collab in creation_details["collaborations"]["existing"]:
            summary += f"\n    - {collab['name']} (ID: {collab['id']})"

    summary += f"\n\nSessions: {len(creation_details['sessions']['created'])} created"
    if creation_details["sessions"]["created"]:
        summary += "\n  Created:"
        for session in creation_details["sessions"]["created"]:
            summary += f"\n    - {session['name']} (ID: {session['id']})"

    if creation_details["dev_folders_cleared"]:
        summary += (
            f"\n\nDev folders cleared: {len(creation_details['dev_folders_cleared'])}"
        )
        for folder in creation_details["dev_folders_cleared"]:
            summary += f"\n  - {folder}"

    summary += "\n\n======================="
    print(summary)
    return summary


def create_fixtures(
    client: Client,
    number_of_nodes: int,
    return_as_dict: bool = False,
    node_config_creation_details: NodeConfigCreationDetails | None = None,
    clear_dev_folders: bool = False,
) -> str | dict:
    """
    Create the fixtures for the server.

    Parameters
    ----------
    client: Client
        The client to use to create the fixtures.
    number_of_nodes: int
        The number of nodes to create.
    return_as_dict: bool
        Whether to return the creation details as a dictionary or as a summary string.
        Default is False.
    node_config_creation_details: NodeConfigCreationDetails | None
        The details to use to create the node configs. If not provided, the node configs
        will not be created.
    clear_dev_folders: bool
        Whether to clear the dev folders.

    Returns
    -------
    str | dict
        The creation summary or the creation details as a dictionary.
    """

    # Track creation details
    creation_details = {
        "organizations": {"created": [], "existing": [], "root_org_patched": []},
        "users": {"created": [], "existing": []},
        "nodes": {"created": [], "existing": []},
        "collaborations": {"created": [], "existing": []},
        "sessions": {"created": []},
        "dev_folders_cleared": [],
    }

    # Remove old config files
    if clear_dev_folders and node_config_creation_details:
        for node_dir in [
            d for d in node_config_creation_details.dev_dir.iterdir() if d.is_dir()
        ]:
            clear_dev_folder(node_config_creation_details.dev_dir, node_dir.name)
            creation_details["dev_folders_cleared"].append(node_dir.name)

    # Create organizations
    organizations, creation_details["organizations"] = create_organizations(
        client, number_of_nodes
    )

    # Create collaboration
    collaboration, creation_details["collaborations"] = create_collaborations(
        client, organizations
    )

    # Create users
    creation_details["users"] = create_users(client, organizations)

    # create collaboration session
    creation_details["sessions"] = create_session(client, collaboration)

    # Create nodes
    for i in range(1, number_of_nodes + 1):
        name = f"node-{i}"
        if next(
            iter(
                [
                    node
                    for node in client.node.list(name=name)["data"]
                    if node["name"] == name
                ]
            ),
            None,
        ):
            creation_details["nodes"]["existing"].append(
                {"name": name, "organization": organizations[i - 1]["name"]}
            )
        else:
            try:
                node = register_node(
                    client,
                    node_name=name,
                    collaboration=collaboration,
                    organization=organizations[i - 1],
                )
                if node_config_creation_details:
                    creation_details["nodes"]["created"].append(
                        create_node_config(
                            node_number=i,
                            node_name=name,
                            dev_dir=node_config_creation_details.dev_dir,
                            task_directory=node_config_creation_details.task_directory,
                            task_namespace=node_config_creation_details.task_namespace,
                            node_starting_port_number=(
                                node_config_creation_details.node_starting_port_number
                            ),
                            node=node,
                            organization=organizations[i - 1],
                        )
                    )
                else:
                    creation_details["nodes"]["created"].append(
                        {
                            "name": name,
                            "organization": organizations[i - 1]["name"],
                            "api_key": node["api_key"],
                        }
                    )

            except Exception as e:
                traceback.print_exc()
                print(f"Error creating node {name}: {str(e)}")

    # Print creation details
    printed_summary = print_creation_details(creation_details)
    if return_as_dict:
        return creation_details
    else:
        return printed_summary
