.. _use-algorithm-store:

Use
---

This section explains which commands are available to manage your algorithm
store. These can be used to set up a test server locally. To deploy a server,
see the :ref:`deployment <algorithm-store-deployment>` section.


Quick start
"""""""""""

To create a new algorithm store, run the command below. A menu will be started
that allows you to set up an algorithm store configuration file.

::

   v6 algorithm-store new

For more details, check out the :ref:`algorithm-store-configure` section.

To run an algorithm store, execute the command below. The ``--attach`` flag will
copy log output to the console.

::

   v6 algorithm-store start --name <your_store> --attach

Finally, a server can be stopped again with:

::

   v6 algorithm-store stop --name <your_store>

Available commands
""""""""""""""""""

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
