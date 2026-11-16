# vantage6 architecture: v4 compared with v5

This comparison is based on the code at tag `version/4.15.4` and on the 5.1 branch. The
5.0.0 release notes call v5 "the largest release in the history of vantage6". The
federated model itself is unchanged: a central component distributes tasks, nodes run
algorithms next to the data, and only results leave a site. Nearly everything around that
model has changed.

## In one table

| Area | v4.x | v5.x |
|---|---|---|
| Central server | "server" (`vantage6-server`) | "HQ" (`vantage6-hq`). HQ, algorithm store, Keycloak and UI together are called the **hub**. |
| Runtime platform | Docker. Each component is a container started by `v6 … start` or docker-compose. | Kubernetes. Each component is installed as a Helm chart (`charts/hq`, `store`, `auth`, `hub`, `node`), and the CLI drives Helm. |
| How the node runs algorithms | The node container mounts the Docker socket and starts sibling containers on an isolated Docker network. | The node pod creates Kubernetes **Jobs** through a namespaced Role. One pod per run. |
| Authentication | Built into the server: username/password JWTs, optional TOTP MFA, nodes log in with an API key at `/token/node`. | Delegated to **Keycloak** (`charts/auth`). Users, nodes and service accounts get OIDC tokens, and MFA reset is admin-only. |
| Data access by algorithms | Every task gets the database URI or file and reads the raw data itself (`@data` decorator). | **Sessions**: a data extraction step writes a dataframe (Parquet) on the node, and later preprocessing and compute steps work on those dataframes. |
| Algorithm steps | One kind of task (federated or central, decided by the algorithm). | Typed steps: `data_extraction`, `preprocessing`, `federated_compute`, `central_compute`, `postprocessing`. |
| Task definition | `input_` holds the method and its arguments (encrypted as one blob). | Separate `method` and `arguments` fields. A task can belong to a session and target a dataframe. |
| Algorithm-to-algorithm traffic | Supported through a **VPN** (EduVPN/OpenVPN client container, port registration via `/port` and `/vpn`). | Removed. Algorithms only talk to HQ through the node proxy. |
| Outbound traffic from algorithms | Isolated Docker network. Whitelisted hosts through a **Squid** proxy container, external services through **SSH tunnel** containers. | Kubernetes **NetworkPolicies**: default deny for algorithm pods, egress to the node proxy and DNS, plus a whitelist of domains/IPs/ports. The node checks isolation at startup. |
| Algorithm input/output | Files in a temporary Docker volume per job (`INPUT_FILE`, `OUTPUT_FILE`, `TOKEN_FILE`). All runs shared that volume. | Files on node storage mounted into the job pod (input, output, session folder). The container token is passed as a Kubernetes Secret. Each run sees only its own files (security fix GHSA-x9f6-9rvm-mmrg). |
| Infrastructure images | node-and-server, vpn-client, vpn-configurator, squid, ssh-tunnel, alpine, ui, algorithm-store | node-and-hq, algorithm-store, ui, alpine, and algorithm base images. The VPN, Squid and SSH tunnel images are gone. |
| Horizontal scaling of HQ | RabbitMQ for socket messages between server instances (optional). | Same idea, now a RabbitMQ deployment in the HQ chart. Prometheus is part of the HQ chart too. |
| Test networks | `v6 dev create-demo-network` (Docker). | `v6 sandbox` (hub + 3 nodes on local Kubernetes) and `v6 dev` (DevSpace with hot reload). |
| Algorithm testing | `MockAlgorithmClient`. | A "mock network" with logical nodes, HQ and users, which can also test extraction steps. |
| Python and packaging | Python ≥ 3.10, `setup.py`, pip, Black. | Python 3.13, `pyproject.toml` with hatchling, `uv` workspace, Ruff. |
| Server libraries | Flask, Flask-SocketIO, SQLAlchemy 1.4 | Flask, Flask-SocketIO, SQLAlchemy 2 |
| Default admin | `root`/`root` | A generated password per production install (`admin`/`admin` only for sandbox and dev). |

## The main changes explained

### 1. From Docker to Kubernetes

This is the biggest structural change, and most other differences follow from it.

**v4 node.** The node is a Python process in a Docker container that has access to the
host's Docker daemon. At startup it creates an isolated Docker network, then starts helper
containers when they are configured: a VPN client, Squid and SSH tunnels. For each run it
creates a temporary volume and an algorithm container on that network, and the node itself
acts as the proxy to the server. Everything assumes one Docker host.

**v5 node.** The node is a Deployment installed by the node Helm chart. It starts
algorithms as Kubernetes Jobs using the Kubernetes API (`k8s/container_manager.py`).
Kubernetes takes over what Docker networks and helper containers used to do:

- RBAC (Role and RoleBinding) controls what the node may create;
- NetworkPolicies isolate algorithms;
- PVCs, mounted with sub paths, provide task storage;
- Secrets carry the container token.

The node still contains the proxy server that algorithms use to reach HQ.

**Consequences.**

- Running a node no longer needs access to a Docker daemon, which hospitals often refuse,
  but it does need a Kubernetes cluster. A single-machine site can use microk8s or similar.
- Installing, upgrading and configuring are Helm operations. The CLI (`v6 node start`,
  `v6 hub start` …) generates values and calls Helm.
- On Docker every algorithm image ran under the same daemon. Pods are now subject to
  cluster policy (SCCs on OpenShift, quotas, required resource limits). This is why this
  branch adds settings for resources, security context and runtime class.

### 2. Authentication through Keycloak

v4 implemented accounts, passwords, MFA, password reset e-mails and node API key login in
the server itself. v5 delegates this to Keycloak, which runs as its own chart (`auth`) and
issues the tokens for UI users, API users, service accounts and nodes. The client and node
use `python-keycloak`, and a node still configures an API key, which is exchanged with
Keycloak. HQ keeps its own role and rule model for **authorization**.

This closes several v4 advisories (unlimited MFA reset mails, MFA bypass through password
reset). It also adds a component to operate and makes the UI depend on Keycloak cookies
(hence the new privacy statement).

### 3. Sessions and dataframes

In v4 every task started from scratch: the algorithm received a database URI or a mounted
file and loaded and preprocessed the raw data on every run.

In v5 the user opens a **session** (HQ models `Session` and `Dataframe`):

1. A `data_extraction` task reads the source database and writes a named dataframe as a
   Parquet file in the session folder on each node.
2. `preprocessing` tasks modify that dataframe, and HQ records the columns for each node.
3. `federated_compute` and `central_compute` tasks read one or more dataframes
   (`USER_REQUESTED_DATAFRAMES`). They never touch the source database.

As a result, algorithms are independent of the database type, since only extraction
algorithms know about CSV, SQL, OMOP and so on. Repeated analyses are faster, and HQ knows
the dataframe schema, which the UI uses. Algorithm code declares its step with decorators
in `vantage6.algorithm.decorator` (`action`, `data`, `algorithm_client`, `ohdsi`). These
replace the v4 `decorators.py`/`wrappers.py`, so **v4 algorithms do not run on v5
without changes**.

### 4. Networking: VPN, Squid and SSH tunnels removed

v4 had three optional networking add-ons on the node:

- a **VPN** for direct communication between algorithm containers at different sites
  (used for MPC-style algorithms), with server endpoints to register ports;
- **Squid** to allow selected outbound HTTP(S) hosts;
- **SSH tunnels** to reach services outside the isolated network.

v5 removes all three. Algorithm pods are isolated by NetworkPolicies, and the node's
`whitelist` setting becomes extra egress rules. On a cluster that does not allow
NetworkPolicies there is no equivalent isolation inside vantage6, so the cluster admin
has to provide it. This branch makes the policies optional and shows a warning in that
case. Algorithms that relied on the VPN for direct peer-to-peer traffic have no
replacement in v5. All traffic goes through HQ.

### 5. Renaming and grouping

- Server → **HQ** (Headquarters), in code, configuration, CLI (`v6 hq …`) and charts.
- **Hub** = HQ + algorithm store + Keycloak + UI, installed as one umbrella chart
  (`charts/hub`) with `v6 hub new/start/stop`.
- The algorithm store already existed in late v4. In v5 it gains `link_algorithms`
  presets and an "update image" option, and it uses the same Keycloak.

### 6. Developer workflow

| | v4 | v5 |
|---|---|---|
| Local network to try things | `v6 dev create-demo-network` + `v6 dev start-demo-network` | `v6 sandbox new/start` |
| Working on vantage6 itself | Rebuild images, restart containers | `v6 dev start` (DevSpace, file sync and hot reload on Kubernetes) |
| Repository | Separate `setup.py` per package, `requirements.txt` | One `uv` workspace, `uv.lock`, `make install-dev` |
| Code style | Black | Ruff (lint and format) |

## What stayed the same

- The roles of organization, collaboration, study, node, task, run, user, role and rule.
- The node polls and listens (Socket.IO) for tasks and only makes **outbound**
  connections to HQ. No inbound port is needed at the hospital.
- The proxy in the node through which algorithms reach HQ, and container tokens limited
  to a task (with expiry since 4.15.3).
- End-to-end encryption of task input and results with organization key pairs.
- Node policies: `allowed_algorithms`, `allowed_algorithm_stores` and the `production`
  flag (introduced in 4.15.3 and kept in v5).
- Algorithms are delivered as Docker/OCI images, and the Angular UI (now Angular 22).

## Upgrading from v4 to v5

There is no in-place upgrade path:

- **Platform**: every component moves from Docker to Kubernetes/Helm.
- **Users and authentication**: users must exist in Keycloak, and v4 passwords and MFA
  secrets do not carry over.
- **Algorithms**: they must be rewritten for the step-typed decorators and dataframes.
  An extraction algorithm is needed for each data source.
- **Algorithms using the VPN or SSH tunnels**: these need a different design.
- **Configuration**: node and server configs follow the Helm values layout (camelCase,
  nested `node:` block).

## Relation to this branch (`feature/node-single-namespace`)

Even in 5.1, the v5 node chart still carried some single-host assumptions from v4:

- algorithms ran in a separate task namespace;
- storage used `local` PersistentVolumes pinned to one machine and hostPath mounts;
- NetworkPolicies were mandatory.

This branch removes those assumptions so that the node and its algorithm pods run in
**one namespace** with **PVCs only**, and NetworkPolicies and the isolation check become
optional. That lets the v5 node run on managed clusters such as DSRI or hospital
OpenShift environments. HQ, store and auth charts still use host-bound PVs.
