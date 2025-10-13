"""
Development script to delete all entities from the server
"""

from vantage6.client import Client


def delete_fixtures(client: Client) -> str:
    """
    Delete all entities from the server.

    Arguments
    ---------
    client: Client
        The client to use to delete the entities.
    """

    # Track deletion counts
    deletion_counts = {}

    # Delete sessions & dataframes
    sessions = client.session.list(per_page=999)["data"]
    for session in sessions:
        client.session.delete(session["id"], delete_dependents=True)
    deletion_counts["sessions"] = len(sessions)

    # Delete tasks and nodes
    for client_subclass_name in ("task", "node"):
        client_subclass = getattr(client, client_subclass_name)
        entities = client_subclass.list(per_page=999)["data"]
        for entity in entities:
            client_subclass.delete(entity["id"])
        deletion_counts[f"{client_subclass_name}s"] = len(entities)

    # Delete collaborations
    collabs = client.collaboration.list(per_page=999, scope="global")["data"]
    for collab in collabs:
        client.collaboration.delete(collab["id"])
    deletion_counts["collaborations"] = len(collabs)

    # Delete users (excluding admin)
    users = client.user.list(per_page=999)["data"]
    deleted_users = 0
    for user in users:
        if user["username"] == "admin":
            continue
        client.user.delete(user["id"])
        deleted_users += 1
    deletion_counts["users"] = deleted_users

    # Delete organizations (excluding the default organization with id 1)
    orgs = client.organization.list(per_page=999)["data"]
    deleted_orgs = 0
    for org in orgs:
        if org["id"] == 1:
            continue
        client.organization.delete(org["id"])
        deleted_orgs += 1
    deletion_counts["organizations"] = deleted_orgs

    # Create summary string
    summary = "=== Deletion Summary ===\n"
    for entity_type, count in deletion_counts.items():
        summary += f"Deleted {count} {entity_type}\n"
    summary += "======================="
    print(summary)
    return summary
