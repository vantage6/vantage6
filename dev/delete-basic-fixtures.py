"""
Development script to delete all entities from the server

The `devspace` commands use this script to clean all tasks, nodes,
collaborations, etc. from the server.
"""

from pathlib import Path

from vantage6.client import Client

dev_dir = Path("dev") / ".data"
dev_dir.mkdir(exist_ok=True)

client = Client("http://localhost", 7601, "/server", log_level="error")
client.authenticate()

print("=> Deleting sessions & dataframes")
for session in (sessions := client.session.list(per_page=999)["data"]):
    client.session.delete(session["id"], delete_dependents=True)
print("==> Deleted", len(sessions), "sessions")

for client_subclass_name in ("task", "node"):
    client_subclass = getattr(client, client_subclass_name)
    print(f"=> Deleting {client_subclass_name}s")
    for entity in (entities := client_subclass.list(per_page=999)["data"]):
        client_subclass.delete(entity["id"])
    print("==> Deleted", len(entities), f"{client_subclass_name}s")


print("=> Deleting collaborations")
for collab in (
    collabs := client.collaboration.list(per_page=999, scope="global")["data"]
):
    client.collaboration.delete(collab["id"])
print("==> Deleted", len(collabs), "collaborations")

print("=> Deleting users")
for user in (users := client.user.list(per_page=999)["data"]):
    if user["username"] == "admin":
        continue
    client.user.delete(user["id"])
print("==> Deleted", len(users) - 1, "users")

print("=> Deleting organizations")
for org in (orgs := client.organization.list(per_page=999)["data"]):
    if org["name"] == "root":
        continue
    client.organization.delete(org["id"])
print("==> Deleted", len(orgs) - 1, "organizations")
