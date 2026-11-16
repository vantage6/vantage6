.. _algorithm-isolation:

Algorithm container isolation
-----------------------------

The algorithms run in vantage6 have access to the sensitive data that we want
to protect. Also, the algorithms may be built improperly, or may be outdated,
which might make it vulnerable to attacks. Therefore, one of the important
security measures that vantage6 implements is that all algorithms run in a
container that is not connected to the internet. The isolation from the internet
is achieved by starting the algorithm container as a Kubernetes job that is not
given access to the internet (neither outbound nor inbound).

.. warning::

  Isolation depends on the Kubernetes cluster enforcing NetworkPolicies. Docker Desktop
  Kubernetes does **not** meet this requirement at the time of writing, making it
  unsuitable for production use. Nodes with setting ``production: true``
  will verify isolation at startup and refuse to run if the check fails.

The node's Helm chart creates these NetworkPolicies in the node's namespace. They
apply to the pods the node starts for algorithm runs, which carry the labels
``v6-pod-type: algorithm`` and ``v6-node-release: <release name>``, and leave other
workloads in the namespace alone.

If you may not create NetworkPolicies, set ``networkPolicy.enabled: false`` in the node
configuration and have your cluster administrator isolate pods with these labels in
another way. Then also set ``networkPolicy.verifyIsolation: false``: the node then
skips its startup check and logs a warning instead. Only do so when you are sure that
isolation is enforced, as the node can no longer detect that it is not.

A node that runs with Docker (see :ref:`node-docker`) isolates algorithm containers
with Docker networks instead: they get no network at all, except central compute
containers, which share an internal network with the node only. Whitelisted HTTP(S)
destinations are reached through a proxy on an internal network of the step. The
node checks isolation at startup in the same way.

.. note::

  Before version 5, vantage6 did not use Kubernetes. Then, algorithms were run in
  isolated Docker networks.

While the algorithm is thus isolated from the internet, it still has to be able
to access several different resources, such as the vantage6 HQ if it needs
to spawn other containers for subtasks. Such communication all takes place over
interfaces that are an integral part of vantage6, and are thus considered safe.
Below is a list of interfaces that are available to the algorithm container.

- Vantage6 HQ is available to the algorithm container via a proxy server
  running on the node.
- Addresses that are explicitly :ref:`whitelisted <node-whitelisting>` by the node owner are made available to the
  algorithm container.

Note that all of these connections are initiated from the algorithm container.
Vantage6 does not support incoming connections to the algorithm container.