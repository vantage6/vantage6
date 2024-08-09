.. _main-intro:

Introduction
============

In many research projects, data is distributed across multiple organizations. This
makes it difficult to perform analyses that require data from multiple sources, as the
data owners don't want to share their data with others. Vantage6 is a platform that
enables privacy-enhancing analyses on distributed data. It allows organizations to
collaborate on analyses while only sharing aggregated results, not the raw data.

As a user, you can use vantage6 to run your algorithms on sensitive data. In order to
create the tasks to run your algorithms, it will be helpful to understand how vantage6
works. In order to help you understand this, we will first explain the basic
architecture of vantage6, followed by a description of the resources that are available
in vantage6. Using those concepts, we will explain give an example of a simple algorithm
and explain how that is run within vantage6.

Vantage6 components
-------------------

In vantage6, a **client** can pose a question to the central **server**. Each organization
with sensitive data contributes one **node** to the network. The nodes collects the
research question from the server and fetches the **algorithm** to answer it.  When the
algorithm completes, the node sends the aggregated results back to the server.

.. _architecture-figure:

.. uml::

    !theme superhero-outline

    left to right direction
    skinparam nodesep 80
    skinparam ranksep 80

    rectangle client as "Client"
    rectangle server as "Server"
    client --> server

    rectangle node1 as "Node 1"
    rectangle node2 as "Node 2"

    server <-- node1
    server <-- node2

    node1 <-r[dashed]-> node2

The roles of these vantage6 components are as follows:

* A (central) **server** coordinates communication with clients and nodes.
  The server tracks the status of the computation requests and handles
  administrative functions such as authentication and authorization.
* **Node(s)** have access to data and execute algorithms
* **Clients** (i.e. users or applications) request computations from the nodes via the
  client
* **Algorithms** are scripts that are run on the sensitive data. Each algorithm is
  packaged in a Docker image; the node pulls the image from a Docker registry and runs
  it on the local data. Note that the node owner can control which algorithms are
  allowed to run on their data.

On a technical level, vantage6 may be seen as a (Docker) container
orchestration tool for privacy preserving analyses. It deploys a network of
containerized applications that together ensure insights can be exchanged
without sharing record-level data.

.. _components:

Vantage6 resources
------------------

There are several entities in vantage6, such as users, organizations,
tasks, etc. These entities are created by users that have sufficient permission to
do so and are stored in a database that is managed by the central server. This process
ensures that the right people have the right access to the right actions, and that
organizations can only collaborate with each other if they agree to do so.

The following statements and the figure below should help you understand
their relationships.

-  A **collaboration** is a collection of one or more **organizations**.
-  For each collaboration, each participating organization needs a **node** to compute
   tasks. When a collaboration is created, accounts are also created for the nodes so
   that they can securely communicate with the server.
-  Collaborations can contain **studies**. A study is a subset of organizations from the
   collaboration that are involved in a specific research question. By setting up
   studies, it can be easier to send tasks to a subset of the organizations in a
   collaboration and to keep track of the results of these analyses.
-  Each organization has zero or more **users** who can perform certain actions.
-  The permissions of the user are defined by the assigned **rules**.
-  It is possible to collect multiple rules into a **role**, which can also be assigned
   to a user.
-  A **session** can contain several **data frames**. A data frame is a collection of
   data retrieved from the original source database. A data frame can be modified by
   additional user defined pre-processing steps and can be used as input for **tasks**.
-  Users can create **tasks** for one or more organizations within a collaboration and
   session. Tasks lead to the execution of the algorithms.
-  A task should produce an algorithm **run** for each organization involved in the
   task. The **results** are part of such an algorithm run.

The following schema is a *simplified* version of the database. A `1-n` relationship
means that the entity on the left side of the relationship can have multiple entities
on the right side. For instance, a single organization can have multiple vantage6 users,
but a single user always belongs to one organization. There is one `0-n` relationship
between roles and organizations, since a role can be coupled to an organization, but it
doesn't have to be. An `n-n` relationship is a many-to-many relationship: for instance,
a collaboration can contain multiple organizations, and an organization can participate
in multiple collaborations.

.. uml::

    !theme superhero-outline
    skinparam nodesep 100
    skinparam ranksep 100
    left to right direction
    skinparam linetype polyline

    rectangle Collaboration
    rectangle Node
    rectangle Organization
    rectangle Session
    rectangle DataFrame
    rectangle Study
    rectangle Task
    rectangle Result
    rectangle User
    rectangle Role
    rectangle Rule

    Collaboration "1" -- "n" Node
    Collaboration "n" -- "n" Organization
    Collaboration "1" -- "n" Study
    Collaboration "1" - "n" Session
    Collaboration "1" -- "n" Task

    Study "n" -left- "n" Organization
    Study "1" -right- "n" Task
    Task "n" -right- "1" Session

    Node "n" -right- "1" Organization

    Organization "1" -- "n" User
    Organization "0" -- "n" Role
    Task "1" - "n" Result
    Session "n" -left- "1" User

    Session "1" -- "n" DataFrame

    User "n" -left- "n" Role
    Role "n" -- "n" Rule
    User "n" -- "n" Rule


A simple federated average algorithm
------------------------------------

To compute an average, you usually sum all the values and divide them by the number of
values. In Python, this can be done as follows:

.. code:: python

    x = [1,2,3,4,5]
    average = sum(x) / len(x)

In a federated data set the values for `x` are distributed over multiple locations.
Let's assume `x` is split into two parties:

.. code:: python

    a = [1,2,3]
    b = [4,5]

In this case we can compute the average as:

.. code:: python

    average = (sum(a) + sum(b))/(len(a) + len(b))

The goal is to compute the average without sharing the individual numbers. In the case
of an average algorithm, each node therefore shares only the sum and the number of
elements in the dataset. The server then computes the average by summing the sums and
dividing by the sum of the number of elements. This way, the individual numbers are
never shared.

How algorithms work in vantage6
-------------------------------

The average algorithm explained above can be separated in a central part and a
federated part. The federated part uses the data to compute the sum and the number
of elements. The central part is the aggregation of these results. In order to do so, it
is also responsible to start the federated parts and to collecting their results.
Note that for more complex algorithms, this can be an iterative process: the central
part can send new tasks to the federated parts based on the results of the previous
round of federated tasks.


.. figure:: /images/algorithm_central_and_subtasks.png
   :alt: Algorithm hierarchy
   :align: center

   Common task hierarchy in vantage6. The user (left) creates a task for the central
   part of the algorithm (pink hexagon). The central part creates subtasks for the
   federated parts (green hexagons). When the subtasks are finished, the central part
   collects the results and computes the final result, which is then available to the
   user.

Now, let's see how this works in vantage6. It is easy to confuse the central server with
the central part of the algorithm: the server is the central part of the infrastructure
but not the place where the central part of the algorithm is executed (:numref:`algorithm-flow`).
The central part
is actually executed at one of the nodes, because it gives more flexibility: for
instance, an algorithm may need heavy compute resources to do the aggregation, and it
is better to do this at a node that has these resources rather than having to upgrade
the server whenever a new algorithm needs more resources.

.. figure:: /images/task_journey.png
   :name: algorithm-flow
   :alt: algorithm-flow
   :align: center

   The flow of the average algorithm in vantage6. The user creates a task for the
   central part of the algorithm. This is registered at the server, and leads to the
   creation of a central algorithm container on one of the nodes. The central algorithm
   then creates subtasks for the federated parts of the algorithm, which again are
   registered at the server. All nodes for which the subtask is intended start their
   work by executing the federated part of the algorithm. The nodes send the results
   back to the server, from where they are picked up by the central algorithm. The
   central algorithm then computes the final result and sends it to the server, where
   the user can retrieve it.

Note that is also possible for the user to create the subtasks directly, and to compute
the central part of the algorithm themselves. This is however not the most common
approach as it is in general easier to let the central algorithm do the work.

How to run algorithms in vantage6
---------------------------------

Once you have set up a vantage6 server and nodes, you are ready to run your algorithms.
You can create tasks from the :ref:`web interface <ui>`, the
:ref:`Python client <use-python-client>` or by interacting with the :ref:`API <server-api>`
directly. There are a number of public algorithms available from the
:ref:`community algorithm store <community-store>`. :ref:`Linking this store <algorithm-store-linking>`
to your server will allow you to quickly get a set of algorithms that you can run on your nodes.

You can also develop your own vantage6 algorithms.
The only requirement is that you package the algorithm in a Docker image that vantage6
can run. The focus of vantage6 is on setting up an
infrastructure to run algorithms on sensitive data and ensuring that the data is kept
private - the algorithm implementation is kept highly flexible.

The freedom in defining the code also allows you to use federated learning libraries such as
`PySyft <https://openmined.github.io/PySyft/index.html>`_, `TensorFlow <https://www.tensorflow.org/>`_ or
`Flower <https://flower.ai/>`_ within your vantage6 algorithm. Also, it is not only
possible to run federated algorithms, but also MPC algorithms or other protocols.

.. note::

    Vantage6 tries to limit the definition of algorithms as little as possible. This
    means that within a project, it should be established which algorithms are allowed
    to run on the nodes. Review of this code - or trust in persons that have created the
    algorithm - is the responsibility of each node owner. They are ultimately in control
    over which algorithms are run on their data.

Vantage6 is designed to be as flexible as possible,
so you can use any programming language and any libraries you like. Python is the most
common language to use within the vantage6 community, and also has the most
:ref:`tools <algo-dev-guide>` available to help you with your work.

