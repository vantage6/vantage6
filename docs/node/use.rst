.. _use-node:

Use
----

This section explains which commands are available to manage your node.

Quick start
^^^^^^^^^^^

To create a new node, run the command below. A menu will be started that
allows you to set up a node configuration file. For more details, check
out the :ref:`configure-node` section.

::

   vnode new

To run a node, execute the command below. The ``--attach`` flag will
cause log output to be printed to the console.

::

   vnode start --name <your_node> --attach

Finally, a node can be stopped again with:

::

   vnode stop --name <your_node>

.. note::

   Before the node is started, it is attempted to obtain the server version.
   For a server of version ``x.y.z``, a node of version ``x.y.<latest>`` is
   started - this is the latest available node version for the server version.
   If no server version can be obtained, the latest node of the same major
   version as the command-line interface installation is started.

Available commands
^^^^^^^^^^^^^^^^^^

Below is a list of all commands you can run for your node(s). To see all
available options per command use the ``--help`` flag,
i.e. ``vnode start --help`` .

+---------------------+------------------------------------------------+
| **Command**         | **Description**                                |
+=====================+================================================+
| ``vnode new``       | Create a new node configuration file           |
+---------------------+------------------------------------------------+
| ``vnode start``     | Start a node                                   |
+---------------------+------------------------------------------------+
| ``vnode stop``      | Stop a nodes                                   |
+---------------------+------------------------------------------------+
| ``vnode files``     | List the files of a node (e.g. config and log  |
|                     | files)                                         |
+---------------------+------------------------------------------------+
| ``vnode attach``    | Print the node logs to the console             |
+---------------------+------------------------------------------------+
| ``vnode list``      | List all existing nodes                        |
+---------------------+------------------------------------------------+
| ``vnode             | Create and upload a new public key for your    |
| create-private-key``| organization                                   |
+---------------------+------------------------------------------------+
| ``vnode             | Update the API key in your node configuration  |
| set-api-key``       | file                                           |
+---------------------+------------------------------------------------+

Local test setup
""""""""""""""""

Check the section on :ref:`use-server-local` of the server if
you want to run both the node and server on the same machine.

.. _node-security: