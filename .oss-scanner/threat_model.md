# Threat model

## What this project does and where untrusted input enters

vantage6 is a federated analysis platform for (mostly medical) data. Data stays at
each organization's **node** (data station). Researchers send tasks via the central
**HQ** server. Nodes pull those tasks and run the requested algorithm as a Docker
container on local data, then return only the results.

The primary attacker goal is **disclosure of record-level data from a node**.
Untrusted input enters through:

- **HQ REST API and WebSockets** (`vantage6-hq/`): requests from users, nodes and
  algorithm containers. There are three identity types (user, node, container), and
  their tokens must never be usable in place of one another.
- **Algorithm store API** (`vantage6-algorithm-store/`): algorithm submissions and
  reviews.
- **Algorithm containers**: these are untrusted. They can reach HQ only through the
  node's local proxy (`vantage6-node/`), and they typically have no internet access.
- **Task fields** (image, method, arguments), which nodes receive from HQ and must
  validate against their local policy (`allowed_algorithms`, image digest).
- **Node configuration and local data**: the node reads its configuration file and
  turns the databases listed there into mounts for algorithm containers; the data
  itself is parsed by the extraction code in `vantage6-algorithm-tools/` (CSV,
  Excel, Parquet, SQL, ...). Malformed config or data must not lead to code
  execution, path traversal or access to data the task was not granted.
- **Poisoned data from other participants**: in a federated analysis, every node
  contributes partial results. One malicious or compromised organization can
  supply manipulated data or partial results to bias a shared model or the
  results returned to other parties. Look for places where the platform trusts
  partial results more than it should, e.g. letting one node's output overwrite
  or impersonate another's.

## Components that matter most / least

- **Most:** HQ authentication and authorization (collaboration and organization
  scoping on every object), node container handling and proxy, algorithm allowlist
  and digest checks on the node, and end-to-end encryption of task input and results.
- **Also in scope:** the algorithm store's review workflow and policies, the Helm
  charts (`charts/`, which set up network isolation and secrets), the Angular UI
  (`vantage6-ui/`) and the CLI (`vantage6/`), which operators use to set up and run
  HQ, nodes and the store.
- **Less important:** the CLI's `sandbox` and `dev` commands, which are only meant
  for local development.

## How to exercise it

- `python utest.py` runs the unit tests of all Python packages offline. HQ and the
  algorithm store tests use a local SQLite database.
- `cd vantage6-ui && npx ng build --configuration development` builds the UI offline.
- A full deployment needs Kubernetes and is not available in this image.

## How you rate severity

- **Critical:** record-level data can leave a node, or an attacker can run an
  image the node's policy does not allow, without valid credentials.
- **High:** authentication bypass, a privilege escalation or cross-collaboration
  access in HQ or the store, forging tokens, or reading encrypted task data without
  the organization's private key.
- **Medium:** the same issues but requiring an already privileged account, or
  disclosure of metadata (users, organizations, task status).
- **Low:** denial of service, and issues that only affect development tooling.

## Anything to leave alone

- A malicious node operator can always read their own local data. Node policies
  protect against malicious users and images, not against the node's owner.
- Statistical attacks through approved algorithms (differencing, model inversion)
  are the algorithm developer's responsibility, as is checking that results are
  truly aggregated. The same goes for robust aggregation against poisoned data
  inside an algorithm. Platform-level flaws that make poisoning possible, such as
  one node tampering with or impersonating another node's results, are in scope.
- Insecure settings that an operator has to configure explicitly (e.g. an empty
  `allowed_algorithms`), and default credentials in the local sandbox.
