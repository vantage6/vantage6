Concepts
=======

.. _architectureoverview:

Architecture
------------

In vantage6, a **client** can pose a question to the **server**, which is then
delivered as an **algorithm** to the **node** (:numref:`architecture-figure`).
When the algorithm completes, the node sends the results back to the client via
the server. An algorithm may be enabled to communicate directly with twin
algorithms running on other nodes.

.. _architecture-figure:
.. figure:: /images/architecture-overview.png
   :alt: Architecture overview
   :align: center

   Vantage6 has a client-server architecture. (A) The client is used by the
   researcher to create computation requests. It is also used to manage users,
   organizations and collaborations. (B) The server contains users,
   organizations, collaborations, tasks and their results. (C) The nodes have
   access to data and handle computation requests from the server.

Conceptually, vantage6 consists of the following parts:

* A (central) **server** that coordinates communication with clients and nodes.
  The server is in charge of processing tasks as well as handling
  administrative functions such as authentication and authorization.
* One or more **node(s)** that have access to data and execute algorithms
* **Users** (i.e. researchers or other applications) that request computations
  from the nodes via the client
* **Organizations** that are interested in collaborating. Each user belongs to
  one of these organizations.
* A **Docker registry** that functions as database of algorithms

On a technical level, vantage6 may be seen as a container
orchestration tool for privacy preserving analyses. It deploys a network of
containerized applications that together ensure insights can be exchanged
without sharing record-level data.

.. _components:

Components
-------------

There are several entities in vantage6, such as users, organizations,
tasks, etc. The following statements should help you understand their
relationships.

-  A **collaboration** is a collection of one or more
   **organizations**.
-  For each collaboration, each participating organization needs a
   **node** to compute tasks.
-  Each organization can have **users** who can perform certain
   actions.
-  The permissions of the user are defined by the assigned **rules**.
-  It is possible to collect multiple rules into a **role**, which can
   also be assigned to a user.
-  Users can create **tasks** for one or more organizations within a
   collaboration.
-  A task should produce a **result** for each organization involved in
   the task.

The following schema is a *simplified* version of the database:

.. figure:: /images/db_model.png

   Simplified database model

End to end encryption
^^^^^^^^^^^^^^^^^^^^^

Encryption in vantage6 is handled at organization level. Whether
encryption is used or not, is set at collaboration level. All the nodes
in the collaboration need to agree on this setting. You can enable or
disable encryption in the node configuration file, see the example in
:ref:`node-configure-structure`.

.. figure:: /images/encryption.png

   Encryption takes place between organizations therefore all nodes and
   users from the a single organization should use the same private key.

The encryption module encrypts data so that the server is unable to read
communication between users and nodes. The only messages that go from
one organization to another through the server are computation requests
and their results. Only the algorithm input and output are encrypted.
Other metadata (e.g. time started, finished, etc), can be read by the
server.

The encryption module uses RSA keys. The public key is uploaded to the
vantage6-server. Tasks and other users can use this public key (this is
automatically handled by the python-client and R-client) to send
messages to the other parties.

.. note::
    The RSA key is used to create a shared secret which is used for encryption
    and decryption of the payload.

When the node starts, it checks that the public key stored at the server
is derived from the local private key. If this is not the case, the node
will replace the public key at the server.

.. warning::
    If an organization has multiple nodes and/or users, they must use the same
    private key.

In case you want to generate a new private key, you can use the command
``vnode create-private-key``. If a key already exists at the local
system, the existing key is reused (unless you use the ``--force``
flag). This way, it is easy to configure multiple nodes to use the same
key.

It is also possible to generate the key yourself and upload it by using the
endpoint ``https://SERVER[/api_path]/organization/<ID>``.