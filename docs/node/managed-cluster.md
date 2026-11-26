# Running a node on a managed Kubernetes cluster

This guide shows how to start, check and stop a vantage6 node on a cluster that someone
else manages and where you only have one namespace. Examples are a hospital's
Kubernetes or OpenShift environment, or the
[DSRI](https://dsri.maastrichtuniversity.nl) of Maastricht University. The DSRI values
below were tested on that cluster.

The node, the algorithm pods it starts, their storage and their network policies all
stay in your namespace. The node chart creates no cluster-wide resources, no
PersistentVolumes and no host paths. For background, see *Running in a single namespace
on a shared cluster* in the node requirements (`docs/node/requirements.rst`).

## 1. Before you start

You need:

- **Tools on your own machine.** The `v6` CLI (`pip install vantage6`), `helm` 3 or
  newer, and `kubectl` (or `oc` on OpenShift).
- **Access to your namespace.** A working kubeconfig context for it. On OpenShift,
  `oc login` creates one. Check it with:

  ```bash
  kubectl config get-contexts
  ```

- **A node account at HQ.** Its API key, plus the URLs of HQ and of the
  authentication service (Keycloak). Pods in your namespace must be able to reach both.
  The node only makes outgoing connections, so no inbound port or ingress is needed.

### Check your permissions

Every command below only reads. Replace `<context>` and `<namespace>` with your own
values.

```bash
K="kubectl --context <context> -n <namespace>"
for r in deployments.apps configmaps secrets services persistentvolumeclaims \
         serviceaccounts roles.rbac.authorization.k8s.io \
         rolebindings.rbac.authorization.k8s.io \
         networkpolicies.networking.k8s.io jobs.batch pods; do
  echo "$r: $($K auth can-i create $r)"
done
$K get serviceaccounts                    # e.g. 'anyuid' on OpenShift
kubectl --context <context> get storageclass
$K get resourcequota,limitrange           # minimum claim size, required limits
```

What the answers mean:

- **All `yes`.** The default settings work.
- **`networkpolicies` is `no`.** Turn network policies off (see step 2) and ask your
  administrator to isolate pods with the label `v6-pod-type: algorithm`. They should only
  be able to reach the node pod and DNS.
- **A `LimitRange` with a minimum claim size.** Make every claim at least that big. DSRI
  requires at least 1Gi.
- **A quota, or a policy that requires resources.** Set requests and limits (see step 2).

### Choose your storage

The node and its algorithm pods share one PersistentVolumeClaim for the input, output
and session files of algorithm runs. Each algorithm pod only mounts its own files.

| Storage class supports | Set `accessMode` to | Effect |
|---|---|---|
| ReadWriteMany (NFS, CephFS, Azure Files, …) | `ReadWriteMany` | Algorithm pods can run on any machine. |
| Only ReadWriteOnce (block storage) | `ReadWriteOnce` | Algorithm pods are scheduled on the node pod's machine. |

On DSRI, use `ocs-storagecluster-cephfs` (ReadWriteMany) or `ocs-storagecluster-ceph-rbd`
(ReadWriteOnce, the default storage class).

### Put file-based data on a claim

CSV, Parquet and Excel files are read from a PersistentVolumeClaim that you create
yourself. The node never uses a path on a machine. One way to create and fill such a
claim:

```bash
cat <<'EOF' | $K apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: hospital-data
spec:
  accessModes: [ReadWriteMany]
  storageClassName: ocs-storagecluster-cephfs   # your storage class
  resources:
    requests: {storage: 1Gi}
---
apiVersion: v1
kind: Pod
metadata:
  name: hospital-data-loader
spec:
  restartPolicy: Never
  containers:
  - name: loader
    image: ghcr.io/vantage6/infrastructure/alpine:latest
    command: ["sleep", "600"]
    resources:
      requests: {cpu: 50m, memory: 64Mi, ephemeral-storage: 64Mi}
      limits: {cpu: 200m, memory: 128Mi, ephemeral-storage: 128Mi}
    volumeMounts: [{name: data, mountPath: /data}]
  volumes:
  - name: data
    persistentVolumeClaim: {claimName: hospital-data}
EOF
$K wait --for=condition=Ready pod/hospital-data-loader
$K cp ./my-data.csv hospital-data-loader:/data/my-data.csv
$K delete pod hospital-data-loader
```

In the node configuration, refer to the claim with `existingClaim: hospital-data` and
the file with `subPath: my-data.csv`. The node mounts it read-only.

## 2. Create the node configuration

```bash
v6 node new --name my-node
```

The questions match the choices above:

- API key, the node's name at HQ, the HQ URL, port and API path (`/hq`), and the
  Keycloak URL;
- the task claim: an existing claim, or a new one with storage class, size and access
  mode;
- databases: for a file, the claim name, the path inside the claim, and the type;
- allowed algorithms and algorithm stores (required, because nodes run with
  `production: true`);
- whether the node may create NetworkPolicies;
- whether your cluster requires resource requests and limits on every pod.

`v6 node files --name my-node` shows where the configuration file is. The file holds
the values for the node Helm chart (everything under `node:`), so you can edit it
directly. The wizard does not ask for some OpenShift settings. On DSRI, add these:

```yaml
node:
  # ... what `v6 node new` wrote ...
  runtimeClassName: selinux
  algorithmPods:
    serviceAccountName: anyuid      # for algorithm images that run as root
    runtimeClassName: selinux
    resources:                      # wizard: "requires resource requests and limits"
      requests: {cpu: 500m, memory: 1Gi, ephemeral-storage: 1Gi}
      limits: {cpu: "4", memory: 8Gi, ephemeral-storage: 10Gi}
  resources:
    requests: {cpu: 250m, memory: 1Gi, ephemeral-storage: 1Gi}
    limits: {cpu: "2", memory: 4Gi, ephemeral-storage: 4Gi}
  persistence:
    tasks:
      storageClass: ocs-storagecluster-cephfs
      accessMode: ReadWriteMany
      size: 10Gi
  logging:
    storageSize: 1Gi                # DSRI refuses claims under 1Gi
  networkPolicy:
    dns:                            # OpenShift DNS, not kube-system:53
      namespace: openshift-dns
      ports: [5353]
```

Other settings you may need:

| Setting | When |
|---|---|
| `networkPolicy.enabled: false` and `networkPolicy.verifyIsolation: false` | You may not create NetworkPolicies. The node then logs a warning that isolation is *not* verified. |
| `persistence.tasks.existingClaim` (+ `subPath`) | Your administrator gives you a claim instead of letting you create one. |
| `logging.persistent: false` | You don't want a claim for log files. Logs then only go to the console (`kubectl logs`). |
| `serviceAccount.create: false` and `serviceAccount.name` | You must use a service account that already exists for the node pod. |
| `algorithmPods.ttlSecondsAfterFinished` | Your cluster requires a TTL on Jobs. The default is 86400 (1 day). |
| `podSecurityContext`, `securityContext` (also under `algorithmPods`) | Your cluster requires explicit security contexts. |
| `image` | You want a specific node image instead of the version that matches HQ. |

If the collaboration uses encryption, create the node's private key secret before you
start the node:

```bash
v6 node create-private-key --name my-node --context <context> --namespace <namespace>
```

## 3. Start the node

Always pass the context and the namespace, so that the CLI doesn't fall back to another
cluster:

```bash
v6 node start --name my-node --context <context> --namespace <namespace>
```

What this does:

- installs the Helm release `vantage6-my-node-user-node` (with `--system`:
  `vantage6-my-node-system-node`) into your namespace;
- takes the chart from `oci://ghcr.io/vantage6/helm/node`. Add `--chart-version` for a
  specific version, or `--local-chart-dir <checkout>/charts` to use a local copy of the
  charts;
- picks the node image: `node.image` from the configuration if set, otherwise the node
  image of the HQ's version.

Add `--attach` to follow the logs right away, or attach later:

```bash
v6 node attach --name my-node --context <context> --namespace <namespace>
# or
kubectl --context <context> -n <namespace> logs -f deploy/vantage6-my-node-user-node
```

### Without the vantage6 CLI

The configuration file is a plain Helm values file, so you can also install the chart
directly:

```bash
helm install vantage6-my-node-user-node oci://ghcr.io/vantage6/helm/node \
  --version <chart version> -f <path to my-node.yaml> \
  --kube-context <context> -n <namespace>
```

## 4. Check that the node works

In the node log, at startup you should see:

1. `Checking that pods for algorithm runs can be created`. The node creates a short-lived
   test pod with the algorithm settings (service account, runtime class, resources).
2. `Algorithm network isolation verified.` A probe pod tries to reach the internet and
   must fail. If network policies are switched off you see
   `Algorithm network isolation is NOT verified` instead.
3. `Node '<name>' authenticated successfully`, followed by the connection to HQ.

The node exits with an error if step 1 fails. With `production: true` it also exits if
step 2 shows that algorithms *can* reach the internet. Then it waits for tasks.

Useful commands:

```bash
$K get pods,pvc                          # node pod Running, claims Bound
$K get jobs,pods -l v6-node-release=vantage6-my-node-user-node   # algorithm runs
$K get events --sort-by=.lastTimestamp | tail -20
```

## 5. Stop the node

```bash
v6 node stop --name my-node --context <context> --namespace <namespace>
```

This uninstalls the Helm release and deletes the algorithm jobs, pods and secrets of
this node that are still running. What stays behind:

| Left over | Why | Remove with |
|---|---|---|
| `<release>-task-pvc` | Annotated `helm.sh/resource-policy: keep`, so task and session files survive a restart. | `$K delete pvc <release>-task-pvc` |
| `<release>-logs-pvc` | Same reason, for log files. | `$K delete pvc <release>-logs-pvc` |
| Your data claims (`existingClaim`) | They are yours, and vantage6 never deletes them. | Yourself. |
| The private key secret (with encryption) | Needed on the next start. | `$K delete secret <name>` |

> Many managed clusters, DSRI included, keep no backups of claims. Only delete a claim
> when you are sure you don't need its contents.

To restart or upgrade (new image, new chart version, changed configuration), stop and
start again, or run `v6 node restart` with the same options. The claims are reused.
Change the storage class or access mode of the task claim only after deleting the old
claim, because these cannot be changed on an existing claim.

## 6. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `minimum storage usage per PersistentVolumeClaim is 1Gi` | A claim is smaller than the cluster allows. Raise `logging.storageSize` and `persistence.tasks.size`. |
| `is attempting to grant RBAC permissions not currently held` | Your account lacks a permission that the node's Role needs (jobs, pods, `pods/log` get, secrets). Ask your administrator for these permissions in the namespace. |
| Pods rejected for missing requests or limits | Set `resources` and `algorithmPods.resources`. |
| Algorithm pod fails with permission errors, or `runAsUser` rejected (OpenShift) | The image wants root. Set `algorithmPods.serviceAccountName` to a service account that may use the `anyuid` SCC (`anyuid` on DSRI). |
| Node exits: `Could not create pods for algorithm runs` | The test pod was rejected. Look at `$K get events` for the reason (quota, SCC, image pull). |
| Node exits: `Algorithm network isolation check failed` | Network policies are not enforced, or algorithm pods can reach the internet. Fix the policies, or switch `verifyIsolation` off only if your administrator isolates algorithm pods. |
| Central algorithms cannot reach the node or resolve names | The DNS policy points at the wrong place. On OpenShift use `networkPolicy.dns: {namespace: openshift-dns, ports: [5353]}`. |
| Algorithm pods stay `Pending` with ReadWriteOnce storage | The node pod's machine is full. Use a ReadWriteMany storage class, or lower `algorithmPods.resources`. |
| `Authentication failed` / `Can't connect to server` in the node log | HQ or Keycloak cannot be reached from the cluster, or the API key or node name is wrong. |
