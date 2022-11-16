Concepts
========

Algorithms are executed at the (vantage6-)node. The node receives a computation
task from the vantage6-server. The node will then retrieve the algorithm,
execute it and return the results to the server.

Algorithms are shared using `Docker images <https://docs.docker.com/get-started
/#what-is-a-container-image>`_ which are stored in a `Docker image registry
<https://docs.vantage6.ai/installation/server/docker-registry>`_ which is
accessible to the nodes. In the following sections we explain the fundamentals
of algorithm containers.

1. `Input & output`_
   Interface between the node and algorithm container
2. `Wrappers`_
   Library to simplify and standardized the node-algorithm input and output
3. `Child containers`_
   Creating subtasks from an algorithm container
4. `Networking`_
   Communicate with other algorithm containers and the vantage6-server
5. `Cross language`_
   Cross language data serialization
6. `Package & distribute`_
   Packaging and shipping algorithms

Input & output
--------------
The algorithm runs in an isolated environment within the data station (node).
As it is important to limit the connectivity and accessability for obvious
security reasons. In order for the algorithm to do its work, it is provided
with several resources.

.. note::

    This section describes the current process. Keep in mind that this is
    subjected to be changed. For more information, please see this `Github
    <https://github.com/vantage6/vantage6/issues/154>`_


Environment variables
^^^^^^^^^^^^^^^^^^^^^
The algorithms have access to several environment variables, see :numref:`Environment variables`. These can be used
to locate certain files or to add local configuration settings into the
container.

.. list-table:: Environment variables
   :widths: 30 70
   :header-rows: 1

   * - Variable
     - Description
   * - ``INPUT_FILE``
     - path to the input file. The input file contains the user defined input
       for the algorithms.

   * - ``TOKEN_FILE``
     - Path to the token file. The token file contains a JWT token which can
       be used to access the vantage6-server. This way the algorithm container
       is able to post new tasks and retrieve results.

   * - ``TEMPORARY_FOLDER``
     - Path to the temporary folder. This folder can be used to store
       intermediate results. These intermediate results are shared between all
       containers that have the same run_id. Algorithm containers which are
       created from an algorithm container themselves share the same run_id.

   * - ``HOST``
     - Contains the URL to the vantage6-server.
   * - ``PORT``
     - Contains the port to which the vantage6-server listens. Is used in
       combination with HOST and API_PATH.
   * - ``API_PATH``
     - Contains the api base path from the vantage6-server.
   * - ``[*]_DATABASE_URI``
     - Contains the URI of the local database. The  ``*``  is replaced by the
       key specified in the node configuration file.

.. note::

    Additional environment variables can be specified in the node configuration
    file using the algorithm_env key. These additional variables are forwarded
    to all algorithm containers.

.. TODO::

    Link to additional environment settings

File mounts
^^^^^^^^^^^
The algorithm container has access to several file mounts.

Input
    The input file contains the user defined input. The user specifies this when a task is created.

