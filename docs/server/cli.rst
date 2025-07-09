Command line interface
======================

.. _use-server:

Core
----

This section explains which commands are available to manage your server. It
also explains how to set up a test server locally and how to manage resources
via an IPython shell.

Quick start
^^^^^^^^^^^

To create a new server, run the command below. A menu will be started
that allows you to set up a server configuration file.

::

   v6 server new

For more details, check out the :ref:`server-configure` section.

To run a server, execute the command below. The ``--attach`` flag will
copy log output to the console.

::

   v6 server start --name <your_server> --attach

.. warning::
    When the server is run for the first time, the following user is created:

    -  username: root
    -  password: root

    It is recommended to change this password immediately.

Finally, a server can be stopped again with:

::

   v6 server stop --name <your_server>

Available commands
^^^^^^^^^^^^^^^^^^

The following commands are available in your environment. To see all the
options that are available per command use the ``--help`` flag,
e.g. ``v6 server start --help``.

+----------------+-----------------------------------------------------+
| **Command**    | **Description**                                     |
+================+=====================================================+
| ``v6 server    | Create a new server configuration file              |
| new``          |                                                     |
+----------------+-----------------------------------------------------+
| ``v6 server    | Start a server                                      |
| start``        |                                                     |
+----------------+-----------------------------------------------------+
| ``v6 server    | Stop a server                                       |
| stop``         |                                                     |
+----------------+-----------------------------------------------------+
| ``v6 server    | List the files that a server is using               |
| files``        |                                                     |
+----------------+-----------------------------------------------------+
| ``v6 server    | Show a server's logs in the current terminal        |
| attach``       |                                                     |
+----------------+-----------------------------------------------------+
| ``v6 server    | List the available server instances                 |
| list``         |                                                     |
+----------------+-----------------------------------------------------+
| ``v6 server    | Run a server instance python shell                  |
| shell``        |                                                     |
+----------------+-----------------------------------------------------+
| ``v6 server    | Import server entities as a batch                   |
| import``       |                                                     |
+----------------+-----------------------------------------------------+
| ``v6 server    | Shows the versions of all the components of the     |
| version``      | running server                                      |
+----------------+-----------------------------------------------------+

.. _use-server-local:

Local test setup
^^^^^^^^^^^^^^^^

If the nodes and the server run at the same machine, you have to make
sure that the node can reach the server.

**Windows and MacOS**

Setting the server IP to ``0.0.0.0`` makes the server reachable
at your localhost (this is also the case when the dockerized version
is used). In order for the node to reach this server, set the
``server_url`` setting to ``host.docker.internal``.

.. warning::
    On the **M1** mac the local server might not be reachable from
    your nodes as ``host.docker.internal`` does not seem to refer to the
    host machine. Reach out to us on Discourse for a solution if you need
    this!

**Linux**

You should bind the server to ``0.0.0.0``. In the node
configuration files, you can then use ``http://172.17.0.1``, assuming you use
the default docker network settings.

.. _server-import:

Batch import
^^^^^^^^^^^^

You can easily create a set of test users, organizations and collaborations by
using a batch import. To do this, use the
``v6 server import /path/to/file.yaml`` command. An example ``yaml`` file is
provided below.

You can download this file :download:`here <components/yaml/batch_import.yaml>`.


.. raw:: html

   <details>
   <summary><a>Example batch import</a></summary>

.. literalinclude :: components/yaml/batch_import.yaml
    :language: yaml

.. raw:: html

   </details>

.. warning::
    All users that are imported using ``v6 server import`` receive the superuser
    role. We are looking into ways to also be able to import roles. For more
    background info refer to this
    `issue <https://github.com/vantage6/vantage6/issues/71>`__.

.. _local-test:

Testing
^^^^^^^

You can test the infrastructure via the ``v6 dev`` and ``v6 test`` commands. The purpose of
``v6 dev`` is to easily setup and run a test server accompanied by `N` nodes locally
(default is 3 nodes). For example, if you have `N = 10` datasets to test a particular
algorithm on, then you can spawn a server and 10 nodes with a single command. By default,
the nodes are given access to a test dataset of olympic medal winners, containing data
on e.g. their age, height, length, weight, medal type and sport.

The ``v6 test`` command is used to run the `v6-diagnostics algorithm <https://github.com/vantage6/v6-diagnostics>`_.
You can run it on an existing network or create a ``v6 dev`` network and run the test on that in one
go.

You can view all available commands in the table below, or alternatively, use
``v6 dev --help``. By using ``--help`` with the individual commands (e.g.
``v6 dev start-demo-network --help``), you can view more details on how to
execute them.

.. warning::

  If you are using Linux without Docker desktop, you will need to run
  ``v6 dev create-demo-network --server-url http://172.17.0.1``. This address points
  towards the localhost from within Docker and thereby ensures that the nodes will be
  able to connect to the local server.

+--------------------------------+-----------------------------------------------------+
| **Command**                    | **Description**                                     |
+================================+=====================================================+
| ``v6 dev create-demo-network`` | Create a new network with server and nodes          |
+--------------------------------+-----------------------------------------------------+
| ``v6 dev start-demo-network``  | Start the network                                   |
+--------------------------------+-----------------------------------------------------+
| ``v6 dev stop-demo-network``   | Stop the network                                    |
+--------------------------------+-----------------------------------------------------+
| ``v6 dev remove-demo-network`` | Remove the network completely                       |
+--------------------------------+-----------------------------------------------------+
| ``v6 test feature-test``       | Run the feature-tester algorithm on an existing     |
|                                | network                                             |
+--------------------------------+-----------------------------------------------------+
| ``v6 test integration-test``   | Create a dev network and run feature-tester on that |
|                                | network                                             |
+--------------------------------+-----------------------------------------------------+

An overview of the tests that the `v6-diagnostics algorithm <https://github.com/vantage6/v6-diagnostics>`_
runs is given below.

- **Environment variables**: Reports the environment variables that are set in the algorithm
  container by the node instance. For example the location of the input,
  token and output files.
- **Input file**: Reports the contents of the input file. You can verify that the input
  set by the client is actually received by the algorithm.
- **Output file**: Writes 'test' to the output file and reads it back.
- **Token file**: Prints the contents of the token file. It should contain a JWT that you
  can decode and verify the payload. The payload contains information like the
  organization and collaboration ids.
- **Temporary directory**: Creates a file in the temporary directory. The temporary directory
  is a directory that is shared between all containers that share the same run id.
  This checks that the temporary directory is writable.
- **Local proxy**: Sends a request to the local proxy. The local proxy is used to reach the
  central server from the algorithm container. This is needed as parent containers
  need to be able to create child containers (=subtasks). The local proxy also
  handles encryption/decryption of the input and results as the algorithm container
  is not allowed to know the private key.
- **Subtask creation**: Creates a subtask (using the local proxy) and waits for the result.
- **Isolation test**: Checks if the algorithm container is isolated such that it can not
  reach the internet. It tests this by trying to reach google.nl, so make sure
  this is not a whitelisted domain when testing.
- **External port test**: Check that the algorithm can find its own ports. Algorithms can
  request a dedicated port for communication with other algorithm containers. The
  port that they require is stored in the Dockerfile using the ``EXPORT`` and
  ``LABEL`` keywords. For example:

  .. code:: Dockerfile

     LABEL p8888="port8"
     EXPOSE 8888

  It however does not check that the application is actually listening on the port.
- **Database readable**: Check if the file-based database is readable.
- **VPN connection**: Check if an algorithm container on the node can reach other
  algorithm containers on other nodes *and* on the same node over the VPN network.
  This test will not succeed if the VPN connection is not set up - it can also be disabled
  with ``v6 test feature-test --no-vpn``.

.. _use-algorithm-store:

Store
-----

This section explains which commands are available to manage your algorithm
store. These can be used to set up a test server locally. To deploy a server,
see the :ref:`deployment <algorithm-store-deployment>` section.


Quick start
^^^^^^^^^^^

To create a new algorithm store, run the command below. A menu will be started
that allows you to set up an algorithm store configuration file.

.. code-block:: bash

   v6 algorithm-store new

For more details, check out the :ref:`algorithm-store-configure` section.

To run an algorithm store, execute the command below. The ``--attach`` flag will
copy log output to the console.

.. code-block:: bash

   v6 algorithm-store start --name <your_store> --attach

Finally, a server can be stopped again with:

.. code-block:: bash

   v6 algorithm-store stop --name <your_store>


Available commands
^^^^^^^^^^^^^^^^^^

The following commands are available in your environment. To see all the
options that are available per command use the ``--help`` flag,
e.g. ``v6 server start --help``.

.. list-table:: Available commands
   :name: algorithm-store-commands
   :widths: 30 70
   :header-rows: 1

   * - Command
     - Description
   * - ``v6 algorithm-store new``
     - Create a new algorithm store configuration file
   * - ``v6 algorithm-store start``
     - Start an algorithm store
   * - ``v6 algorithm-store stop``
     - Stop an algorithm store
   * - ``v6 algorithm-store files``
     - List the files that an algorithm store is using
   * - ``v6 algorithm-store attach``
     - Show an algorithm store's logs in the current terminal
   * - ``v6 algorithm-store list``
     - List the available algorithm store instances