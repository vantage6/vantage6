.. _algo-concepts:

Algorithm concepts
==================

This page details the concepts used in vantage6 algorithms. Understanding
these concepts is helpful when you to create your own algorithms. A guide to
develop your own algorithms can be found in the :ref:`algo-dev-guide`.

Algorithms are executed at the vantage6 node. The node receives a computation
task from the vantage6-server. The node will then retrieve the algorithm,
execute it and return the results to the server.

Algorithms are shared using `Docker images <https://docs.docker.com/get-started
/#what-is-a-container-image>`_ which are stored in a `Docker image registry
<https://docs.vantage6.ai/installation/server/docker-registry>`_. The node
downloads the algorithms from the Docker registry. In the following sections we
explain the fundamentals of algorithm containers.

1. `Algorithm structure`_: The typical structure of an algorithm
2. `Input & output`_: Interface between the node and algorithm container
3. `Wrappers`_: Library to simplify and standardized the node-algorithm input
   and output
4. `Child containers`_: Creating subtasks from an algorithm container
5. `Networking`_: Communicate with other algorithm containers and the
   vantage6-server
6. `Cross language`_: Cross language data serialization

Algorithm structure
-------------------

Multi-party analyses commonly have a central part and a
remote part. The remote part is responsible for the actual analysis and the
central part is often responsible for aggregating the partial results of
the remote parts. An alternative to aggregating is orchestration, where
the central part does not combine the partial results itself, but instead
orchestrates the remote parts in a certain way that also leads to a global
result. Of course, the central part may also do both aggregation and
orchestration.

In vantage6, we refer to the orchestration part as the **central function** and
the federated part as the **partial function**.

A common pattern for a central function would be:

1. Request partial models from all participants
2. Obtain the partial models
3. Combine the partial models to a global model
4. (optional) Repeat step 1-3 until the model converges

In vantage6, it is possible to run only the partial parts of the analysis on the
nodes and combine them on your own machine, but it is usually preferable to run
the central part within vantage6, because:

-  You don't have to keep your machine running during the analysis
-  The results are stored on the server, so they may also be accessed by other
   users

.. note::
    Central functions also run at a node and *not* at the server. For more
    information, see `here <https://vantage6.ai/news/algorithm-journey/>`_.

Input & output
--------------

The algorithm runs in an isolated environment at the data station.
It is important to limit the connectivity and accessability of an algorithm
run for security reasons. For instance, by default, algorithms cannot access the
internet.

In order for the algorithm to do its work, it needs to be provided with several
environment variables and file mounts. The exact environment variables that
are available to algorithms are described in the :ref:`algo-env-vars` section.
The available file mounts are described below.

.. note::

    This section describes the current process. Keep in mind that this is
    subjected to be changed. For more information, please see this `Github issue
    <https://github.com/vantage6/vantage6/issues/154>`_

.. TODO we might want to move this to a more technical section of the docs
.. as it is not very relevant to most readers

.. _algo-file-mounts:

File mounts
^^^^^^^^^^^

The algorithm container has access to several file mounts. These files mounts
are provided by the vantage6 infrastructure, so the algorithm developer does
not need to provide these files themselves. They can access these files using
the environment variables described in the :ref:`algo-env-vars` section.

The available file mounts are:

*Input*
    The input file contains the user defined input. The user specifies this
    when a task is created.

*Output*
    The algorithm writes its output to this file. When the docker
    container exits, the contents of this file will be send back to the
    vantage6-server.

*Token*
    The token file contains a JWT token which can be used by the algorithm
    to communicate with the central server. The token can only be used to
    create a new task with the same image, and is only valid while the task
    has not yet been completed.

*Temporary directory*
    The temporary directory can be used by an algorithm container to share
    files with other algorithm containers that:

    -  run on the same node
    -  have the same ``job_id``

    Algorithm containers share a ``job_id`` as long as they originate from
    the same user-created task. Child containers (see :ref:`algo-child-containers`)
    therefore have the same ``job_id`` as their parent container.

The paths to these files and directories are stored in the environment
variables, which we will explain now.

.. _wrapper-concepts:

Wrappers
--------

The vantage6 algorithm wrappers simplifies and standardizes the interaction
between algorithm and node. The algorithm wrapper does the following:

-  read the data from the database(s) and provide it to the algorithm
-  read the environment variables and file mounts and supply these to
   your algorithm.
-  select the appropriate algorithm function to run. In more detail, this means
   that it provides an
   `entrypoint <https://docs.docker.com/engine/reference/builder/#entrypoint>`_
   for the Docker container
-  write the output of your algorithm to the output file

Using the wrappers allows algorithm developers to write a single algorithm for
multiple types of data sources, because the wrapper is responsible for reading
the data from the database(s) and providing it to the algorithm. Note however
that algorithms cannot be run using databases that are not supported by the
wrapper. The wrapper currently supports the following database types listed
:ref:`here <wrapper-function-docs>`.

The wrapper is language specific and currently we support Python and R.
Extending this to other languages is usually simple.

.. figure:: /images/algorithm_wrapper.png

   The algorithm wrapper handles algorithm input and output.

.. TODO
.. Data serialization
.. ^^^^^^^^^^^^^^^^^^

.. _algo-child-containers:

Child containers
----------------

When a user creates a task, one or more nodes spawn an algorithm
container. These algorithm containers can create new tasks themselves.

Every algorithm is supplied with a JWT token (see `Input & output`_).
This token can be used to communicate with the vantage6-server. In case
you use an algorithm wrapper, you can supply an ``AlgorithmClient`` using
the :ref:`appropriate decorator <implementing-decorators>`.

A child container can be a parent container itself. There is no limit to
the amount of task layers that can be created. It is common to have only
a single parent container which handles many child containers.

.. figure:: /images/container_hierarchy.png

   Each container can spawn new containers in the network. Each
   container is provided with a unique token which they can use to
   communicate to the vantage6-server.

The token to which the containers have access supplies limited permissions to
the container. For example, the token can be used to create additional tasks,
but only in the same collaboration, and using the same image.

Networking
----------

The algorithm container is deployed in an isolated network to reduce their
exposure. Hence, the algorithm it cannot reach the internet. There are two
exceptions:

1. When the VPN feature is enabled on the server all algorithm
   containers are able to reach each other using an ``ip`` and
   ``port`` over VPN.
2. The central server is reachable through a local proxy service. In the
   algorithm you can use the ``HOST``, ``POST`` and ``API_PATH`` to find
   the address of the server.

.. note::
    We are working on a whitelisting feature which allows a node to
    configure addresses that the algorithm container is able to reach.

VPN connection
^^^^^^^^^^^^^^

Algorithm containers within the same task can communicate directly with each
other over a VPN network. More information on that can be found
:ref:`here <vpn-feature>` and :ref:`this section <vpn-in-algo-dev>` describes
how to use it in an algorithm.

Cross language
--------------

Because algorithms are exchanged as Docker images they can be
written in any language. This is an advantage as developers can use
their preferred language for the problem they need to solve.

.. warning::
    The wrappers are only available for Python and (partially) R, so when
    you use different language you need to handle the IO yourself. Consult the
    `Input & Output`_ section on what the node supplies to your algorithm
    container.

When data is exchanged between the user and the algorithm they both need
to be able to read the data. When the algorithm uses a language specific
serialization (e.g. a ``pickle`` in the case of Python or ``RData`` in
the case of R) the user needs to use the same language to read the
results. A better solution would be to use a type of serialization that
is not specific to a language. In our wrappers we use JSON for this
purpose.

.. note::
    Communication between algorithm containers can use language specific
    serialization as long as the different parts of the algorithm use the same
    language.