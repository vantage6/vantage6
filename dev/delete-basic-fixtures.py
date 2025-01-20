from pathlib import Path

from vantage6.client import Client

dev_dir = Path("dev") / ".data"
dev_dir.mkdir(exist_ok=True)

client = Client("http://localhost", 7601, "/api", log_level="error")
client.authenticate("root", "root")

print("=> Deleting tasks")
for task in (tasks := client.task.list(per_page=999)["data"]):
    client.task.delete(task["id"])
print("==> Deleted", len(tasks), "tasks")

print("=> Deleting nodes")
for node in (nodes := client.node.list(per_page=999)["data"]):
    client.node.delete(node["id"])
print("==> Deleted", len(nodes), "nodes")

print("=> Deleting collaborations")
for collab in (
    collabs := client.collaboration.list(per_page=999, scope="global")["data"]
):
    client.collaboration.delete(collab["id"])
print("==> Deleted", len(collabs), "collaborations")

print("=> Deleting users")
for user in (users := client.user.list(per_page=999)["data"]):
    if user["username"] == "root":
        continue
    client.user.delete(user["id"])
print("==> Deleted", len(users) - 1, "users")

print("=> Deleting organizations")
for org in (orgs := client.organization.list(per_page=999)["data"]):
    if org["name"] == "root":
        continue
    client.organization.delete(org["id"])
print("==> Deleted", len(orgs) - 1, "organizations")
