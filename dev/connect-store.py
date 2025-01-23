from vantage6.client import Client
from pathlib import Path

dev_dir = Path("dev") / ".data"
dev_dir.mkdir(exist_ok=True)

client = Client("http://localhost", 7601, "/api", log_level="error")
client.authenticate("root", "root")

existing_stores = client.store.list().get("data", [])
existing_urls = [store["url"] for store in existing_stores]

# TODO make the path settable
local_store_url = f"http://localhost:7602/store"
if not local_store_url in existing_urls:
    client.store.create(
        algorithm_store_url=local_store_url,
        name="local store",
        all_collaborations=True,
        force=True,  # required to link localhost store
    )
