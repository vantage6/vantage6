.. _node-docker:

Running a node with Docker
--------------------------

A node can also run on a single machine with Docker instead of on Kubernetes. The
node then runs as a container that starts the algorithm containers next to it,
through the Docker socket that is mounted in the node container. The central hub
(HQ, authentication, algorithm store) still runs on Kubernetes; a hub can have
nodes of both kinds.

Requirements
^^^^^^^^^^^^

- Docker Engine on Linux (also rootless), or Docker Desktop on macOS or Windows
  (WSL 2)
- Python 3.13 with the ``vantage6`` package (:ref:`install-node`)

Helm, ``kubectl`` and a kubeconfig are not needed.

Create and start the node
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   v6 node new --runtime docker
   v6 node start --name <name>

``v6 node new --runtime docker`` asks the same questions as for a Kubernetes node,
except that file databases are files or folders on this machine, and that you can
limit the CPUs and memory of algorithm containers. The configuration file starts
with ``runtime: docker``.

The other ``v6 node`` commands work as usual: ``list`` shows where each node runs,
``attach`` shows its logs, ``stop`` removes the node container together with its
algorithm containers and networks, and ``remove`` deletes its configuration. If
encryption is enabled, ``v6 node create-private-key`` stores the private key in a
file next to the node configuration that only you can read.

What runs where
^^^^^^^^^^^^^^^

- The **node container** ``vantage6-<name>-<user|system>-node`` is started with
  restart policy ``unless-stopped``. It mounts the Docker socket, its configuration
  (read-only), the task folder ``<data folder>/tasks``, its log folder and the file
  databases (read-only unless their ``mount_mode`` is ``copy``).
- Each **algorithm run** gets a container that only mounts the input and output
  file of that run and the folder of its session.
- **Networks**: steps without network access (the default for all steps but
  central compute) get no network at all. Central compute containers share an
  internal network with the node, so that they can reach the node proxy and nothing
  else. At startup the node checks that they cannot reach the internet; with
  ``production: true`` it refuses to start if they can.

Whitelisting
^^^^^^^^^^^^

Algorithm steps can be allowed to reach HTTP(S) destinations. The node then starts
a Squid proxy for that step on an internal network of its own, and passes the proxy
to the algorithm in ``HTTP_PROXY`` and ``HTTPS_PROXY``:

.. code-block:: yaml

   node:
     whitelist:
       data_extraction:
         http:
           domains: [".example.org"]
           ips: ["10.0.0.0/8"]
           ports: [443]

Only HTTP and HTTPS work through the proxy. A database that is reached with another
protocol, such as PostgreSQL, is not reachable from algorithm containers of a Docker
node; use a file database or a Kubernetes node for it. The Kubernetes ``egress``
rules are refused on a Docker node.

Limits and security options
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: yaml

   node:
     docker:
       algorithmContainers:
         cpus: 4
         memory: 8g
         pids_limit: 4096
         gpus: all
         cap_drop: [ALL]

``no-new-privileges`` is set by default, and privileged containers are refused. An
algorithm container that runs out of memory is reported as crashed, with the reason
in its log.

Support images
^^^^^^^^^^^^^^

Besides the node image, a Docker node pulls three small images that are published
with vantage6: ``curl`` for the isolation check, ``alpine`` for the check that
algorithm containers can read the task files, and ``squid`` for whitelisting. If
your machine cannot reach ``ghcr.io``, point them at your own registry:

.. code-block:: yaml

   node:
     docker:
       networkIsolation:
         probeImage: registry.example.org/curl:8
       preflightImage: registry.example.org/alpine:3
       squidImage: registry.example.org/vantage6/squid:5.1.0

Security
^^^^^^^^

.. warning::

   Access to the Docker socket gives full control over the machine. Anyone who can
   change the node container, or the users in the ``docker`` group, can therefore
   act as root on it. Algorithm containers never get the socket.

- Use **rootless Docker** where possible: a compromised node is then limited to an
  unprivileged user.
- The API key and the container tokens are visible to those who can run
  ``docker inspect`` on the machine.
- Two runs of the same algorithm step that run at the same time can reach each
  other over their shared network. On Kubernetes they cannot.

Docker Desktop
^^^^^^^^^^^^^^

On Docker Desktop, Docker translates the paths of the node's folders; the node
reads the translated paths from its own container, so algorithm containers get the
same files. If the Docker API is not at one of the usual locations, set
``node.docker.host`` (e.g. ``unix:///Users/me/.docker/run/docker.sock``) in the node
configuration, or the ``DOCKER_HOST`` environment variable.
