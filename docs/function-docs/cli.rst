Command line interface
======================

This page contains the API reference of the functions in the vantage
package. This package contains the Command-Line Interface (CLI) of the
Vantage6 framework.

.. TODO It would be nice to just do the following here
.. .. click:: vantage6.cli.cli:cli_complete
   ..   :prog: v6
   ..   :nested: full
.. But that leads to the names of the actual functions being listed rather
.. than the names of the commands (e.g. v6 server cli_server_files i.o.
.. v6 server files). So we have to do it manually for now.

Node CLI
--------

vantage6.cli.node
+++++++++++++++++

.. click:: vantage6.cli.cli:cli_node
    :prog: v6 node
    :nested: full

Server CLI
----------

.. click:: vantage6.cli.cli:cli_server
    :prog: v6 server
    :nested: full

Local test setup CLI
--------------------

.. click:: vantage6.cli.cli:cli_dev
    :prog: v6 dev
    :nested: full

.. _node-context-class:

vantage6.cli.context
---------------------

.. automodule:: vantage6.cli.context
   :members:
   :show-inheritance:

.. automodule:: vantage6.cli.context.node
   :members:
   :show-inheritance:

.. automodule:: vantage6.cli.context.server
   :members:
   :show-inheritance:

.. automodule:: vantage6.cli.context.algorithm_store
   :members:
   :show-inheritance:

.. automodule:: vantage6.cli.context.base_server
   :members:
   :show-inheritance:

vanatge6.cli.configuration_manager
----------------------------------

.. automodule:: vantage6.cli.configuration_manager
   :members:
   :show-inheritance:

vantage6.cli.configuration_wizard
---------------------------------

.. automodule:: vantage6.cli.configuration_wizard
   :members:
   :show-inheritance:

vanatge6.cli.rabbitmq.queue_manager
-----------------------------------

.. automodule:: vantage6.cli.rabbitmq.queue_manager
   :members:

vanatge6.cli.rabbitmq
----------------------

.. automodule:: vantage6.cli.rabbitmq
   :members:


vantage6.cli.utils
------------------

.. automodule:: vantage6.cli.utils
   :members: