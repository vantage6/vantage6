"""
Development script to populate the server
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from vantage6.cli.globals import PACKAGE_FOLDER, APPNAME


def clear_dev_folder(dev_dir: Path, name: str) -> None:
    node_dev_dir = dev_dir / name
    if node_dev_dir.exists():
        for file_ in node_dev_dir.iterdir():
            file_.unlink()
        node_dev_dir.rmdir()
        print(f"===> Dev folder for node `{name}` cleared")


def create_fixtures(
    client,
    number_of_nodes,
    task_directory,
    task_namespace,
    node_starting_port_number,
    dev_dir,
) -> str:

    # Track creation details
    creation_details = {
        "organizations": {"created": [], "existing": []},
        "users": {"created": [], "existing": []},
        "nodes": {"created": [], "existing": []},
        "collaborations": {"created": [], "existing": []},
        "dev_folders_cleared": [],
    }

    # Remove old config files
    for node_dir in [d for d in dev_dir.iterdir() if d.is_dir()]:
        clear_dev_folder(dev_dir, node_dir.name)
        creation_details["dev_folders_cleared"].append(node_dir.name)

    # Create organizations
    organizations = []
    for i in range(1, number_of_nodes + 1):
        name = f"org_{i}"
        if org := next(iter(client.organization.list(name=name)["data"]), None):
            creation_details["organizations"]["existing"].append(
                {"name": name, "domain": org["domain"]}
            )
            organizations.append(org)
        else:
            org = client.organization.create(
                name=name,
                address1=f"address 1 {i}",
                address2=f"address 2 {i}",
                zipcode=f"1234AB {i}",
                country="NL",
                domain=f"org{i}.org",
            )
            creation_details["organizations"]["created"].append(
                {"name": name, "domain": org["domain"]}
            )
            organizations.append(org)

    # Create collaboration
    if col_1 := next(
        iter(client.collaboration.list(scope="global", name="collab 1")["data"]), None
    ):
        creation_details["collaborations"]["existing"].append(
            {"name": "collab 1", "id": col_1["id"]}
        )
    else:
        col_1 = client.collaboration.create(
            name="collab 1",
            organizations=[org["id"] for org in organizations],
            encrypted=False,
        )
        creation_details["collaborations"]["created"].append(
            {"name": "collab 1", "id": col_1["id"]}
        )

    # Create users
    users = []
    for index, org in enumerate(organizations):
        username = f"user_{index + 1}"
        if user := next(iter(client.user.list(username=username)["data"]), None):
            creation_details["users"]["existing"].append(
                {
                    "username": username,
                    "organization": org["name"],
                }
            )
            users.append(user)
        else:
            password = "Password123!"
            user = client.user.create(
                username=username,
                password=password,
                organization=org["id"],
                roles=[1],  # TODO assign proper roles
            )
            creation_details["users"]["created"].append(
                {
                    "username": username,
                    "password": password,
                    "organization": org["name"],
                }
            )
            users.append(user)

    # Create nodes
    for i in range(1, number_of_nodes + 1):
        name = f"node_{i}"
        if next(iter(client.node.list(name=name)["data"]), None):
            creation_details["nodes"]["existing"].append(
                {"name": name, "organization": organizations[i - 1]["name"]}
            )
        else:
            try:
                # Create a folder for all config files for a single node
                node_dev_dir = dev_dir / name
                node_dev_dir.mkdir(exist_ok=True)

                node = client.node.create(
                    collaboration=col_1["id"],
                    organization=organizations[i - 1]["id"],
                    name=name,
                )

                # Generate node configuration
                environment = Environment(
                    loader=FileSystemLoader(
                        PACKAGE_FOLDER / APPNAME / "cli" / "template"
                    ),
                    trim_blocks=True,
                    lstrip_blocks=True,
                    autoescape=True,
                )
                template = environment.get_template("node_config.j2")

                node_config = template.render(
                    {
                        "logging": {"file": f"node_{i}.log"},
                        "port": 7601,
                        "server_url": "http://vantage6-server-vantage6-server-service",
                        "task_dir": task_directory,
                        "api_path": "/server",
                        "task_namespace": task_namespace,
                        "node_proxy_port": node_starting_port_number + (i - 1),
                    }
                )
                config_file = node_dev_dir / f"node_org_{i}.yaml"
                with open(config_file, "w") as f:
                    f.write(node_config)

                # Create .env file for the node
                env_file = node_dev_dir / ".env"
                with open(env_file, "w") as f:
                    f.write(f"V6_API_KEY={node['api_key']}\n")
                    f.write(f"V6_NODE_NAME={name}\n")

                creation_details["nodes"]["created"].append(
                    {
                        "name": name,
                        "organization": organizations[i - 1]["name"],
                        "api_key": node["api_key"],
                        "config_file": str(config_file),
                        "env_file": str(env_file),
                    }
                )

            except Exception as e:
                print(f"Error creating node {name}: {str(e)}")

    # Build detailed summary string
    summary = "=== Creation Summary ===\n"

    summary += f"\nOrganizations: {len(creation_details['organizations']['created'])} "
    summary += f"created, {len(creation_details['organizations']['existing'])} existing"
    if creation_details["organizations"]["created"]:
        summary += "\n  Created:"
        for org in creation_details["organizations"]["created"]:
            summary += f"\n    - {org['name']} ({org['domain']})"
    if creation_details["organizations"]["existing"]:
        summary += "\n  Existing:"
        for org in creation_details["organizations"]["existing"]:
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
            summary += f"\n      Config: {node['config_file']}"
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

    if creation_details["dev_folders_cleared"]:
        summary += (
            f"\n\nDev folders cleared: {len(creation_details['dev_folders_cleared'])}"
        )
        for folder in creation_details["dev_folders_cleared"]:
            summary += f"\n  - {folder}"

    summary += "\n\n======================="
    print(summary)
    return summary
