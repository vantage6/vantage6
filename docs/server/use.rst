.. _use-server:

Use
---

This section explains which commands are available to manage your server. It
also explains how to set up a test server locally and how to manage resources
via an IPython shell.

Quick start
"""""""""""

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
""""""""""""""""""

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
""""""""""""""""

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
""""""""""""

You can easily create a set of test users, organizations and collaborations by
using a batch import. To do this, use the
``v6 server import /path/to/file.yaml`` command. An example ``yaml`` file is
provided below.

You can download this file :download:`here <yaml/batch_import.yaml>`.


.. raw:: html

   <details>
   <summary><a>Example batch import</a></summary>

.. literalinclude :: yaml/batch_import.yaml
    :language: yaml

.. raw:: html

   </details>

.. warning::
    All users that are imported using ``v6 server import`` receive the superuser
    role. We are looking into ways to also be able to import roles. For more
    background info refer to this
    `issue <https://github.com/vantage6/vantage6/issues/71>`__.


Testing
"""""""

You can test the infrastructure via the ``vdev`` commands. The purpose of this
functionality is to easily setup and run a test server accompanied by `N` nodes
locally. For example, if you have `N = 10` datasets to test a particular
algorithm on, then you can spawn a server and 10 nodes with a single command.

You can view all available commands in the table below, or alternatively, use
``vdev --help``. By using ``--help`` with the individual commands (e.g.
``vdev start-demo-network --help``), you can view more details on how to execute
them.


+------------------------------+--------------------------------------------+
| **Command**                  | **Description**                            |
+==============================+============================================+
| ``vdev create-demo-network`` | Create a new network with server and nodes |
+------------------------------+--------------------------------------------+
| ``vdev start-demo-network``  | Start the network                          |
+------------------------------+--------------------------------------------+
| ``vdev stop-demo-network``   | Stop the network                           |
+------------------------------+--------------------------------------------+
| ``vdev remove-demo-network`` | Remove the network completely              |
+------------------------------+--------------------------------------------+
