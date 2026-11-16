.. _node-requirements:

Requirements
------------

.. note::
    This section is almost the same as the :ref:`hub requirements <hub-requirements>` section - the
    requirements for all vantage6 components are very similar.

.. |requirement-public-ip| replace:: \
.. |requirement-OS| replace:: , MacOS Big Sur+, Windows 10+
.. |installation-note| replace:: \
    The hardware requirements of the node also depend on the algorithms that
    the node will run. For example, you probably need more compute power for a
    machine learning model than for a descriptive statistical algorithm.


.. include:: ../common/requirements-node-hub.rst

.. _node-requirements-cluster:

Running in a single namespace on a shared cluster
"""""""""""""""""""""""""""""""""""""""""""""""""

The node, the algorithms it runs, their storage and their network policies all live
in one Kubernetes namespace. The node chart creates no cluster-wide resources, so the
node can run on a managed cluster where you only have access to one namespace, such as
a hospital's cluster or an OpenShift project.

**Permissions.** You need to be able to create the following in your namespace:
Deployments, Services, ConfigMaps, Secrets, ServiceAccounts, Roles, RoleBindings and
PersistentVolumeClaims, and, if your cluster allows them, NetworkPolicies. The node's
own service account gets a Role that lets it create, watch and delete jobs, pods (and
their logs) and secrets in that namespace.

.. warning::

    Because algorithms run in the node's namespace, the node's service account can
    read and delete *all* secrets and pods in that namespace, not just its own. Do not
    share the namespace with workloads whose secrets the node should not see.

**Storage.** The node creates PersistentVolumeClaims and relies on the cluster to
provision volumes for them; it never creates PersistentVolumes or uses host paths. The
claim for task files is shared by the node and its algorithm pods:

- With a ``ReadWriteMany`` storage class (e.g. NFS, CephFS, Azure Files), algorithm
  pods can run on any machine of the cluster.
- With ``ReadWriteOnce`` storage, algorithm pods are scheduled on the same machine as
  the node pod, so they can mount the same volume.

Each algorithm pod only mounts the files of its own run. File-based databases (CSV,
Parquet, ...) are read from a PersistentVolumeClaim that you create and fill
beforehand; set ``existingClaim`` and ``subPath`` for them in the node configuration.

**Network isolation.** Algorithm pods are isolated with NetworkPolicies, which allow
them to reach only the node proxy and the cluster DNS. If you may not create
NetworkPolicies, set ``networkPolicy.enabled`` and ``networkPolicy.verifyIsolation`` to
``false``, and make sure your cluster administrator prevents pods with label
``v6-pod-type: algorithm`` from reaching anything but the node pod. See
:ref:`algorithm container isolation <algorithm-isolation>`.

**Pod requirements.** Clusters may reject pods without resource requests and limits,
or require a specific service account or runtime class. Set these with
``resources``, ``runtimeClassName`` and ``podSecurityContext`` for the node pod, and
under ``algorithmPods`` for the pods that run algorithms.

**Example: OpenShift.** On an OpenShift project, e.g. the Data Science Research
Infrastructure of Maastricht University, values like these apply:

.. code-block:: yaml

    node:
      resources:
        requests: {cpu: 250m, memory: 1Gi, ephemeral-storage: 1Gi}
        limits: {cpu: "2", memory: 4Gi, ephemeral-storage: 4Gi}
      algorithmPods:
        # for algorithm images that must run as root
        serviceAccountName: anyuid
        resources:
          requests: {cpu: 500m, memory: 1Gi, ephemeral-storage: 1Gi}
          limits: {cpu: "4", memory: 8Gi, ephemeral-storage: 10Gi}
      persistence:
        tasks:
          storageClass: ocs-storagecluster-cephfs
          accessMode: ReadWriteMany
      networkPolicy:
        dns:
          namespace: openshift-dns
          ports: [5353]
