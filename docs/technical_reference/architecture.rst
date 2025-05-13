Architecture
============

Network Actors
--------------

As we saw before, the vantage6 :ref:`network <architecture-figure>` consists of a
central server, a number of nodes and a client. This section explains in some
more detail what these network actors are responsible for, and which subcomponents they
contain.

Server
++++++

The vantage6 server is the central point of contact for all communication in
vantage6. However, it also relies on other infrastructure components to function
properly. The following components are required for proper functioning of the server.

**Vantage6 server**
    Contains the users, organizations, collaborations, tasks and their results.
    It handles authentication and authorization to the system and is the
    central point of contact for clients and nodes.

**Docker registry**
    Contains algorithms stored in `images <https://en.wikipedia.org/wiki/OS-level_virtualization>`_
    which can be used by clients to request a computation. The node will
    retrieve the algorithm from this registry and execute it.

**Algorithm store (optional but recommended)**
    The algorithm store is intended to be used as a repository for trusted algorithms
    within a certain project. Algorithm stores can be coupled to specific collaborations
    or to all collaborations on a given server. Note that you can also couple the
    community algorithm store (https://store.cotopaxi.vantage6.ai) to your server.
    This store contains a number of community algorithms that you may find useful.

    .. note::
        The algorithm store is required when using the :ref:`user interface <ui-component>`. If no algorithm
        store is coupled to collaborations, no algorithms can be run from the user
        interface. It is also possible to couple collaborations to an algorithm store
        that you do not host yourself.

**VPN server (optional)**
    If algorithms need to be able to engage in peer-to-peer communication, a
    VPN server can be set up to help them do so. This is usually the case when
    working with MPC, and is also often required for machine learning
    applications.

**RabbitMQ message queue (optional)**
    The *vantage6 server* uses the socketIO protocol to communicate between
    server, nodes and clients. If there are multiple instances of the vantage6
    server, it is important that the messages are communicated to all relevant
    actors, not just the ones that a certain server instance is connected to.
    RabbitMQ is therefore used to synchronize the messages between multiple
    *vantage6 server* instances.


Data Station
++++++++++++

**Vantage6 node**
    The node is responsible for executing the algorithms on the **local data**.
    It protects the data by allowing only specified algorithms to be executed after
    verifying their origin. The **node** is responsible for picking up the
    task, executing the algorithm and sending the results back to the server. The
    node needs access to local data. For more details see the
    :ref:`technical documentation of the node <node-api-refs>`.

**Database**
    The database may be in any format that the algorithms relevant to your use
    case support. The currently supported database types are listed
    :ref:`here <wrapper-function-docs>`.

**Algorithm**
    When the node receives a task from the central server, it will download the
    algorithm from the Docker registry and execute it on the local data. The algorithm
    is therefore a temporary component that is automatically created by the node and
    only present during the execution of a task.

User or Application
+++++++++++++++++++

Users or applications can interact with the vantage6 server in order
to create tasks and retrieve their results, or manage entities at the server (i.e.
creating or editing users, organizations and collaborations).

The vantage6 server is an API, which means that there are many ways to interact
with it programatically. There are however a number of applications available that make
is easier for users to interact with the vantage6 server. These are explained in more
detail in the :ref:`User guide <user-guide>` but are also briefly mentioned here:

.. _ui-component:

**User interface**
    The :ref:`user interface <ui>` is a web application that allows users to interact with
    the server. It is used to create and manage organizations, collaborations,
    users, tasks and algorithms. It also allows users to view and download the results
    of tasks. Use of the user interface recommended for ease of use.

**Python client**
    The `vantage6 python client <python-client>` is a Python package that allows users
    to interact with the server from a Python environment. This is helpful for data
    scientists who want to integrate vantage6 into their existing Python workflow.

**API**
    It is also possible to interact with the server :ref:`using the API directly <server-api>`.

.. note::
    There is also an :ref:`R client <r-client>` but this is not actively maintained and
    does not support all functionality.

Learn more?
+++++++++++

If you want to learn more about specific components or features of vantage6, check out
the :ref:`feature section <feature-docs>` of the documentation. It contains detailed
information about the different features of vantage6 and how to use them.