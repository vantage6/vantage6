Architecture
============

*An overview of the vantage6 infrastructure and its components*

Overview
--------

Vantage6 uses both a client-server and peer-to-peer model. In the figure below
the **client** can pose a question to the **server**, the question is then
delivered as an algorithm to the node. When the algorithm completes, the results
are sent back to the client via the server. An algorithm can communicate
directly with other algorithms that run on other nodes if required.

.. figure:: /images/architecture-overview.png
   :alt: Architecture overview
   :align: center

   Vantage6 has a client-server architecture. The Researcher interacts with
   the server to create computation requests and to manage user accounts,
   organizations and collaborations. The Server contains users, organizations,
   collaborations, tasks and their results. The Node has access to data and
   handles computation requests from the server.

The server is in charge of processing the tasks as well as of handling
administrative functions such as authentication and authorization.
Conceptually, vantage6 consists of the following parts:

* A (central) **server** that coordinates communication with clients and nodes
* One or more **node(s)** that have access to data and execute algorithms
* **Organizations** that are interested in collaborating;
* **Users** (i.e. researchers or other applications) that request computations
  from the nodes
* A **Docker registry** that functions as database of algorithms;

Components
----------

In this section we explain each of the individual components that are part of the vantage6 network.

Server
++++++

.. note::
    When we refer to the server, this is not just the vantage6 server, but also
    other infrastructure components that the vantage6 server relies on.

The server is responsible for coordinating all communication in the vantage6
network. It consists of several components:

* vantage6-server
* Docker registry
* VPN server (optionally)
* RabbitMQ message queue (optionally)

The **vantage6 server** contains the users, organizations, collaborations, tasks
and their results. It handles authentication and authorization to the system and
is the central point of contact for clients and nodes.
The **Docker registry**  contains algorithms which can be used by clients to
request a computation.
The **VPN server** is required if algorithms need to be able to engage in
peer-to-peer communication.;

Node
++++

The node is responsible for executing the algorithms on the **local data**.
It protects the data by allowing only specified algorithms to be executed after
verifying their origin. The **vantage6-node** is responsible for picking up the
task, executing the algorithm and sending the results back to the server. The
node needs access to local data. This data can either be a file (e.g. csv) or a
service (e.g. a database).

Researcher
++++++++++

A user interacts only with the server. They can create
tasks and retrieve their results, or manage entities at the server (i.e.
creating or editing users, organizations and collaborations).
