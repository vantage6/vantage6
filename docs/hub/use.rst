Use
======================

.. _use-hub:

Hub
-----

You can manage the hub as a whole using the `v6 hub` command, and manage individual
components using their respective commands, i.e. `v6 hq`, `v6 algorithm-store`,
`v6 auth`.

To quickly set up a local environment, see the :ref:`quickstart` section.

Production - Quick start
^^^^^^^^^^^^^^^^^^^^^^^^

To create a new vantage6 hub, run the command below. A questionnaire will be started
that allows you to set up configuration files for the hub's components, i.e. for HQ,
algorithm store, and authentication service.

::

   v6 hub new

For more details, check out the :ref:`hub-configure` section.

To run a vantage6 hub, execute the command below.

::

   v6 hub start --name <your_hub>

To show the current logs of the hub components, you can use the following commands:

::

   v6 hq attach
   v6 algorithm-store attach
   v6 auth attach

Finally, a vantage6 hub can be stopped again with:

::

   v6 hub stop --name <your_hub>

Available commands
^^^^^^^^^^^^^^^^^^

The following commands are available for the hub as a whole. To see all the
options that are available per command use the ``--help`` flag,
e.g. ``v6 hub start --help``.

.. list-table:: Available commands
   :name: hub-commands
   :widths: 30 70
   :header-rows: 1

   * - Command
     - Description
   * - ``v6 hub new``
     - Create configuration files for all hub's components
   * - ``v6 hub start``
     - Start the hub
   * - ``v6 hub stop``
     - Stop the hub

Managing individual components
------------------------------

The individual components of the hub can be managed separately. The separate commands
offer more options, since some actions cannot be performed on the hub as a whole. For
example, the ``attach`` command that shows the logs would be confusing if shown for all
components simultaneously.

Available commands
^^^^^^^^^^^^^^^^^^

The commands ``v6 hq``, ``v6 algorithm-store`` and ``v6 auth`` contain roughly the same
set of subcommands. Below, the commands they have in common are listed, as example for
HQ.

.. list-table:: Commands available for all hub components
   :name: hq-commands
   :widths: 30 70
   :header-rows: 1

   * - Command
     - Description
   * - ``v6 hq start``
     - Start HQ
   * - ``v6 hq stop``
     - Stop HQ
   * - ``v6 hq files``
     - List the files that HQ is using
   * - ``v6 hq attach``
     - Show HQ's logs in the current terminal
   * - ``v6 hq remove``
     - Remove the configuration files and data directories associated with HQ
   * - ``v6 hq list``
     - List the available HQ instances


There are also a few commands that are specific to a certain hub component. These are
listed below.

.. list-table:: Commands available only for specific hub components
   :name: hq-commands
   :widths: 30 70
   :header-rows: 1

   * - Command
     - Description
   * - ``v6 hq import``
     - Import HQ entities such as organizations, users and collaborations
   * - ``v6 hq version``
     - Shows the HQ version.
   * - ``v6 algorithm-store version``
     - Shows the algorithm store version.
   * - ``v6 auth install-keycloak``
     - Installs custom Kubernetes resources required to run the authentication service.

To see all the options that are available per command use the ``--help`` flag, e.g.
``v6 hq start --help``.

.. _local-test:

Testing
^^^^^^^

You can test the infrastructure via the ``v6 sandbox`` and ``v6 test`` commands. The purpose of
``v6 sandbox`` is to easily setup and run a test hub accompanied by `N` nodes locally
(default is 3 nodes). For example, if you have `N = 10` datasets to test a particular
algorithm on, then you can spawn a hub and 10 nodes with a single command. By default,
the nodes are given access to a test dataset of olympic medal winners, containing data
on e.g. their age, height, length, weight, medal type and sport.

The ``v6 test`` command is used to run the `v6-diagnostics algorithm <https://github.com/vantage6/v6-diagnostics>`_.
You can run it on an existing network or create a ``v6 sandbox`` network and run the
test on that in one go.

You can view all available commands in the table below, or alternatively, use
``v6 sandbox --help``. By using ``--help`` with the individual commands (e.g.
``v6 sandbox start --help``), you can view more details on how to
execute them.

+--------------------------------+-----------------------------------------------------+
| **Command**                    | **Description**                                     |
+================================+=====================================================+
| ``v6 sandbox new``             | Create a new network, and start it                  |
+--------------------------------+-----------------------------------------------------+
| ``v6 sandbox start``           | Start the network                                   |
+--------------------------------+-----------------------------------------------------+
| ``v6 sandbox stop``            | Stop the network                                    |
+--------------------------------+-----------------------------------------------------+
| ``v6 sandbox remove``          | Remove the network completely                       |
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
- **Input file**: Reports the contents of the input file, usually the algorithm method
  and its arguments. You can verify that the input
  set by the client is actually received by the algorithm.
- **Output file**: Writes 'test' to the output file and reads it back.
- **Token**: Check that central compute tasks receive a token through the environment
  variables.
- **Local proxy**: Sends a request to the local proxy. The local proxy is used to reach
  HQ from the algorithm container. This is needed as parent containers
  need to be able to create child containers (=subtasks). The local proxy also
  handles encryption/decryption of the algorithm arguments and results as the algorithm
  container is not allowed to know the private key.
- **Subtask creation**: Creates a subtask (using the local proxy) and waits for the result.
- **Isolation test**: Checks if the algorithm container is isolated such that it can not
  reach the internet. It tests this by trying to reach google.nl, so make sure
  this is not a whitelisted domain when testing.
- **Database readable**: Check if the file-based database is readable.

Import resources into HQ
^^^^^^^^^^^^^^^^^^^^^^^^

.. note::

  If you are using a sandbox or development environment, a test set of users,
  organizations and collaborations is created for you automatically.

You can easily create a set of test users, organizations and collaborations by
using a batch import. To do this, use the
``v6 hq import /path/to/file.yaml`` command. An example ``yaml`` file is
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
    All users that are imported using ``v6 hq import`` receive all permissions.
    Therefore, this should only be used for testing purposes.
