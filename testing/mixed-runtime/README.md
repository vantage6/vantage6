# Mixed-runtime end-to-end test

One collaboration with a Kubernetes node and a Docker node. The test checks that
both runtimes run the same session side by side: data extraction on both nodes,
then a central task whose federated subtasks run on both nodes, with the sum over
both datasets as result.

| Node | Runtime | Data |
|---|---|---|
| `mixed-k8s` | Kubernetes (e.g. an OpenShift project) | `kubernetes.csv` (sum of `value`: 60) |
| `mixed-docker` | Docker (e.g. Docker Desktop on a laptop) | `docker.csv` (sum of `value`: 10) |

Expected result: 70.

The hub (HQ and Keycloak) runs on the cluster and must be reachable from the
Docker node.

## Cluster notes

- Some clusters require CPU, memory and ephemeral-storage requests and limits on
  every container (e.g. a Kyverno policy). Set them on the hub, the node
  (`node.resources`) and algorithm pods (`node.algorithmPods.resources`), and on
  build pods if you build the node image on the cluster.
- Pass `--context` and `--namespace` to every `kubectl`, `oc` and `helm` command.

## 1. Images

- Node image: build it from the branch under test, e.g. with `make image`, or on an
  OpenShift cluster with a binary build of the sources. Set it as `node.image` for
  both nodes.
- Support images: the Docker node needs `ghcr.io/vantage6/infrastructure/curl`,
  `alpine` and, with a whitelist, `squid` of its version. If they are not
  published for that version, set `node.docker.networkIsolation.probeImage`,
  `node.docker.preflightImage` and `node.docker.squidImage` to images you can pull,
  e.g. `curlimages/curl:8.11.1` and `alpine:3`, and build `docker/squid.Dockerfile`.

## 2. Hub

Deploy HQ and Keycloak on the cluster, e.g. with the hub chart. Expose both (e.g.
with OpenShift Routes) and use these URLs for both nodes, so that tokens have the
same issuer everywhere. An algorithm store is not needed.

## 3. Organisations, collaboration and nodes

```bash
python testing/mixed-runtime/run_test.py --hq-url <hq url>/hq \
    --auth-url <keycloak url> --setup
```

This prints the collaboration id, the API key of each node and the password of the
user `mixed-researcher` in `mixed-k8s`, who runs the test (the root user is not a
member of the collaboration).

The script logs in in the browser. With `--password-login <user>` (password in
`V6_PASSWORD`) it logs in with a password instead; that needs direct access grants
on Keycloak's `public_client`, and a user without required actions such as
`UPDATE_PASSWORD`.

## 4. Kubernetes node

Install the node chart from the branch under test as in
`docs/node/managed-cluster.md`, with the API key of `mixed-k8s`, the node image,
`kubernetes.csv` on a claim as file database `default`, and
`^ghcr\.io/vantage6/algorithm/session-basics` as allowed algorithm.

## 5. Docker node

```bash
v6 node new --runtime docker --name mixed-docker
#  API key of mixed-docker, the HQ and Keycloak URLs,
#  file database "default" = testing/mixed-runtime/docker.csv,
#  allowed algorithm: ^ghcr\.io/vantage6/algorithm/session-basics
v6 node start --name mixed-docker --attach
```

The log must show `Algorithm containers can be started with docker` and
`Algorithm network isolation verified.`

If the Docker engine cannot pull from `ghcr.io` (an organisation-managed Docker
Desktop may deny it), pull the algorithm image elsewhere, load it with its
`ghcr.io` name and set `node.policies.require_algorithm_pull: false` for the Docker
node.

## 6. Run the test

```bash
python testing/mixed-runtime/run_test.py \
    --hq-url <hq url>/hq --auth-url <keycloak url> \
    --collaboration <id> \
    --image ghcr.io/vantage6/algorithm/session-basics:5 \
    --compute-args '{"column": "value"}'
```

`session-basics:5` has `read_csv(connection_details)` and `global_sum(column)`. The
script ends with `PASSED`, or `FAILED: <reason>` and exit code 1.

## 7. Checks beyond the script

- `docker inspect` an algorithm container of `mixed-docker` while it runs: only the
  input, output and session folder are mounted, and federated steps have network
  mode `none`.
- `docker restart vantage6-mixed-docker-user-node` while a task runs: its result
  must still arrive.
- Kill a running task: its run is reported as killed and its container or job is
  removed.
- `v6 node stop --name mixed-docker`: `docker ps -a --filter label=vantage6.node_id`
  and `docker network ls --filter label=vantage6.node_id` show nothing of the node.

## 8. Clean up

Uninstall the node release and the hub, and remove the Docker node with
`v6 node remove --name mixed-docker`.
