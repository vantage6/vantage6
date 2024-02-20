Architecture
============

Network Actors
--------------

As we saw in Figure :numref:`architecture-figure`, vantage6 consists of a
central server, a number of nodes and a client. This section explains in some
more detail what these network actors are responsible for.

Server
++++++

.. note::
    When we refer to the server, this is not just the *vantage6 server*, but
    also other infrastructure components that the vantage6 server relies on.

The server is responsible for coordinating all communication in the vantage6
network. It consists of several components:

**vantage6 server**
    Contains the users, organizations, collaborations, tasks and their results.
    It handles authentication and authorization to the system and is the
    central point of contact for clients and nodes.

**Docker registry**
    Contains algorithms stored in `Images <https://en.wikipedia.org/wiki/OS-level_virtualization>`_
    which can be used by clients to request a computation. The node will
    retrieve the algorithm from this registry and execute it.

**VPN server (optionally)**
    If algorithms need to be able to engage in peer-to-peer communication, a
    VPN server can be set up to help them do so. This is usually the case when
    working with MPC, and is also often required for machine learning
    applications.

**RabbitMQ message queue (optionally)**
    The *vantage6 server* uses the socketIO protocol to communicate between
    server, nodes and clients. If there are multiple instances of the vantage6
    server, it is important that the messages are communicated to all relevant
    actors, not just the ones that a certain server instance is connected to.
    RabbitMQ is therefore used to synchronize the messages between multiple
    *vantage6 server* instances.


Data Station
++++++++++++

**vantage6 node**
    The node is responsible for executing the algorithms on the **local data**.
    It protects the data by allowing only specified algorithms to be executed after
    verifying their origin. The **node** is responsible for picking up the
    task, executing the algorithm and sending the results back to the server. The
    node needs access to local data. For more details see the
    :ref:`technical documentation of the node <node-api-refs>`.

**database**
    The database may be in any format that the algorithms relevant to your use
    case support. The currently supported database types are listed
    :ref:`here <wrapper-function-docs>`.


User or Application
+++++++++++++++++++

.. todo add refs for client/UI

A user or application interacts with the *vantage6 server*. They can create
tasks and retrieve their results, or manage entities at the server (i.e.
creating or editing users, organizations and collaborations). This can be done
using clients or via the user interface.


End to end encryption
---------------------

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
vantage6 server. Tasks and other users can use this public key (this is
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
``v6 node create-private-key``. If a key already exists at the local
system, the existing key is reused (unless you use the ``--force``
flag). This way, it is easy to configure multiple nodes to use the same
key.

It is also possible to generate the key yourself and upload it by using the
endpoint ``https://SERVER[/api_path]/organization/<ID>``.