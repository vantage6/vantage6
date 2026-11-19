---
name: sandbox
description: Run a local vantage6 sandbox (hub + nodes on Kubernetes) to verify changes end to end, with images built from the current checkout for the components that changed, and clean it up afterwards. Use when the user asks to start, test against, rebuild, or remove a sandbox.
---

# Sandbox: run, verify, clean up

A sandbox is a full vantage6 hub (Keycloak, HQ, algorithm store, UI) plus nodes, deployed
with Helm on the local Kubernetes cluster by `v6 sandbox`. Use it to check that a change
works across components, not just in unit tests.

Only run `v6 sandbox` commands when the user asked for a sandbox: they create and delete
infrastructure. Do not run `kubectl`; everything below works through `v6` and Docker.

## 1. Before starting

- Run commands from the checkout whose code you want to test, with its dev environment
  installed (`make install-dev`), using `uv run v6 ...`.
- Check that no other sandbox is running, as they share ports (`docker ps` shows
  Kubernetes pods as `k8s_...` containers on Docker Desktop).
- Pick a short sandbox name, e.g. after the branch (`fix2648`). It prefixes all
  resources and node configs (`<name>-node-1`, ...).

## 2. Build images for the components you changed

Only build an image when the change touches code that runs inside it. Every component you
leave out uses the released default image.

| Changed code | Image to build | Pass as |
|---|---|---|
| `vantage6-hq`, `vantage6-backend-common` | `docker/node-and-hq.Dockerfile` | `--hq-image` |
| `vantage6-node` | `docker/node-and-hq.Dockerfile` | `--node-image` |
| `vantage6-common` | `docker/node-and-hq.Dockerfile` | `--hq-image` and/or `--node-image`, wherever the changed code runs |
| `vantage6-algorithm-store` (or shared code it uses) | `docker/algorithm-store.Dockerfile` | `--store-image` |
| `vantage6-ui` | `docker/ui.Dockerfile` | `--ui-image` |
| `vantage6` (CLI), `vantage6-client` | none: they run from the checkout via `uv run` | |
| `charts/` | none: pass `--local-chart-dir charts` | |

Build with plain `docker build` and a simple local tag, from the repo root. Do not use
`make image` or push to a registry: local images work because the charts use
`imagePullPolicy: IfNotPresent`.

```bash
docker build -t <name>-node -f docker/node-and-hq.Dockerfile .
docker tag <name>-node <name>-hq            # HQ and node share this image
docker build -t <name>-ui -f docker/ui.Dockerfile .
docker build -t <name>-store -f docker/algorithm-store.Dockerfile .
```

Build in parallel in the background; it takes a few minutes. Then confirm that the image
contains the change, e.g. by importing a new name:
`docker run --rm --entrypoint python <name>-node -c "from vantage6.node import ..."`.

## 3. Create the sandbox

```bash
uv run v6 sandbox new --name <name> [--hq-image <name>-hq] [--node-image <name>-node] \
  [--ui-image <name>-ui] [--store-image <name>-store] [--encrypted] < /dev/null
```

- Run it in the background. Populating HQ logs in with the device flow: a browser tab
  opens and **the user must log in** (`admin` / `admin`). Tell the user before starting.
- `--encrypted` creates an encrypted collaboration, with a private key per node stored in
  a Kubernetes secret. Only use it when the change involves encryption.
- If data directories fail to mount (WSL), retry with `--data-dir <path>` and pass the
  same `--data-dir` to `remove` later.

The output ends with a creation summary: organizations, users (`user_N` /
`Password123!`), nodes, the collaboration `demo`, a session, and the algorithm store's
id. The hub config path is printed as `New configuration created:
.../hub/<name>.sandbox.yaml`; its `global.urls.external` section has the URLs. Defaults:

| Component | URL |
|---|---|
| UI | http://localhost:30760 |
| HQ API | http://localhost:30761/hq |
| Algorithm store | http://localhost:30762/store |
| Keycloak (auth) | http://localhost:30764 |

Blob storage is not configured, so tests in the sandbox do not cover the blob-store or
streaming code paths.

## 4. Check that it runs your code

- `docker ps --format '{{.Image}} {{.Names}}' | grep <name>` shows each pod's image ID;
  compare it with `docker images | grep <name>`.
- Node logs (`docker logs <k8s_vantage6-node_...>`) should show `Connected to HQ`.

## 5. Run tasks

### Python client

Create dataframes and tasks with `store=`, so they refer to the algorithm in the store:
the UI then shows the function, its arguments and the results instead of a warning that
the algorithm could not be retrieved.

```python
import time

from vantage6.client import Client

client = Client(hq_url="http://localhost:30761/hq", auth_url="http://localhost:30764")
client.authenticate()  # device flow: the user approves the login in the browser
org_id = client.whoami.organization_id  # WhoAmI has .name, not .username
store_id = client.store.list(collaboration=1)["data"][0]["id"]

df = client.dataframe.create(
    label="olympic-athletes",
    image="ghcr.io/vantage6/algorithm/extract-basics:latest",
    method="read_csv",
    arguments={},
    session=1,
    store=store_id,
    name=f"check_{int(time.time())}",  # dataframe names must be unique
)
client.wait_for_results(df["last_session_task"]["id"])

task = client.task.create(
    collaboration=1,
    organizations=[org_id],
    name="check",
    image="ghcr.io/vantage6/algorithm/demo/average:latest",
    description="",
    method="central_average",
    arguments={"column_name": "Age"},  # only the function's own arguments
    session=1,
    store=store_id,
    databases=[{"dataframe_id": df["id"]}],
    action="central_compute",
)
print(client.wait_for_results(task["id"]))
```

- The algorithms in the sandbox store and their arguments are listed at
  `http://localhost:30762/store/algorithm`.
- The node datasets are CSV files under the sandbox data directory
  (`.../dev/<name>/node/`), which you can use to compute expected results.
- `central_average` creates subtasks, which exercises the node proxy.
- In an encrypted collaboration, call `client.setup_encryption(<pem>)` after
  `authenticate()`. The key is the node key of the user's organization; read it with
  `read_private_key_secret` from `vantage6.cli.node.common.private_key` (not `kubectl`)
  and keep it outside the repo.

### UI

The user drives the UI: log in at http://localhost:30760 and create a task from an
algorithm in the store. Give them exact steps (algorithm, function, arguments,
organizations, dataframe). In an encrypted collaboration they first upload their
organization's private key.

## 6. Debugging

- HQ logs: `docker logs $(docker ps -q --filter name=k8s_vantage6-hq_vantage6-<name>)`.
- Node logs: same, with `k8s_vantage6-node_vantage6-<name>-node-<i>`.
- Algorithm output and crashes: the node shares algorithm logs with HQ. Read them from
  the client (`client.run.get(<id>)`) or from HQ's database:
  `docker exec <k8s_postgres_vantage6-<name>-user-hub-hq-postgres...> sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select id, status, log from run where task_id=<id>;"'`.
- Raw data as HQ stores it: `client.request("run", params={"task_id": ...})` for arguments
  and `client.request("result", params={"task_id": ...})` for results.

## 7. Rebuild after a code change

Rebuild the changed images with the same tags (step 2), then restart. Stop and start
keeps HQ's database, organizations and keys:

```bash
uv run v6 sandbox stop --name <name>
uv run v6 sandbox start --name <name>
```

Check the new image IDs as in step 4. Use `v6 sandbox start --re-initialize` to
repopulate HQ and recreate node configs.

## 8. Clean up

When the user is done (ask first; this deletes the sandbox's data):

```bash
uv run v6 sandbox stop --name <name>     # remove refuses while the hub runs
uv run v6 sandbox remove --name <name> [--data-dir <path>]
```

`remove` deletes the node and hub configs, the nodes' private-key secrets, the node data
and the hub. Then remove what it leaves behind:

- **Data directory:** files written by the database and node containers are owned by
  other users, so `remove` may warn `Permission denied` for `.../dev/<name>`. Delete it
  from a container instead of with `sudo`:
  `docker run --rm --user 0 --entrypoint sh -v <dev-dir>:/d <any-local-image-with-sh> -c 'rm -rf /d/<name>'`.
  Check that only the shared datasets remain in the dev directory.
- **Images:** `docker rmi` the images you built in step 2 (several GB).
- **Files you created for testing**, such as scripts and exported private keys.
- Confirm nothing is left: `docker ps | grep <name>` and `docker images | grep <name>`
  return nothing.
