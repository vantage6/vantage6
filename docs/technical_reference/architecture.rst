Architecture
============

Network Actors
--------------

As we saw before, the vantage6 :ref:`network <vantage6-components-intro>` consists of a
vantage6 hub, a number of nodes and a client. This section explains in some
more detail what these network actors are responsible for, and which subcomponents they
contain.

Hub
+++

The vantage6 hub is the central point of contact for communication in
vantage6. The hub components are listed in more detail in the
:ref:`hub-admin-guide` section.

Data Station
++++++++++++

The data station is the collection of all components running at the data partner's site.

**Vantage6 node**
    The node is responsible for executing the algorithms on the **local data**.
    It protects the data by allowing only specified algorithms to be executed after
    verifying their origin. The **node** is responsible for picking up the
    task, executing the algorithm and sending the results back to HQ. The
    node needs access to local data. For more details see the
    :ref:`technical documentation of the node <node-api-refs>`.

**Database**
    The database may be in any format that the algorithms relevant to your use
    case support. The currently supported database types are listed
    :ref:`here <wrapper-function-docs>`.

**Algorithm**
    When the node receives a task from HQ, it will download the
    algorithm from the container registry and execute it on the local data. The
    algorithm is therefore a temporary component that is automatically created by the
    node and only present during the execution of a task.

User or Application
+++++++++++++++++++

Users or applications can interact with the vantage6 hub in order
to create tasks and retrieve their results, or manage entities at the hub (i.e.
creating or editing users, organizations, collaborations and managing algorithms).

The vantage6 hub contains multiple APIs (for the server, the store and the
authentication service), which means that there are many ways to interact
with it programatically. There are however a number of applications available that make
is easier for users to interact with the vantage6 hub. These are explained in more
detail in the :ref:`User guide <user-guide>` but are also briefly mentioned here:

**User interface**
    The :ref:`user interface <ui>` is the easiest way
    to interact with the vantage6 hub.

**Python client**
    The :ref:`vantage6 python client <python-client>` is a Python package that allows users
    to interact with HQ from a Python environment. This is helpful for data
    scientists who want to integrate vantage6 into their existing Python workflow.

**API**
    It is also possible to interact with the hub :ref:`using the APIs directly <hq-api>`.

Learn more?
+++++++++++

The next sections describe specific features of vantage6 in more detail. Check them out!
