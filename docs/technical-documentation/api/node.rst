.. _node-api-refs:

Node
====

.. automodule:: vantage6.node

-----------------------

Below you will find the structure of the classes and functions that
comprise the node. A few that we would like to highlight:

* :ref:`Node <node-class>`: the main class in a vantage6 node.
* :ref:`NodeContext <node-context-class>` and
  :ref:`DockerNodeContext <docker-node-context-class>`: classes that handle
  the node configuration. The latter inherits from the former and adds some
  properties for when the node runs in a docker container.
* :ref:`DockerManager <docker-manager-class>`: Manages the docker containers
  and networks of the vantage6 node.
* :ref:`DockerTaskManager <task-manager-class>`: Start a docker container that
  runs an algorithm and manage its lifecycle.
* :ref:`VPNManager <vpn-manager-class>`: Sets up the VPN connection (if it is
  configured) and manages it.
* :ref:`vnode-local commands <vnode-local-module>`: commands to run
  non-dockerized (development) instances of your nodes.

-------------------------

.. _node-class:

``Node`` class
--------------
.. autoclass:: vantage6.node.Node
   :members:
   :private-members: __proxy_server_worker, __start_task, __listening_worker,
     __speaking_worker

.. _node-context-class:

``NodeContext`` class
---------------------
.. autoclass:: vantage6.cli.context.NodeContext
   :members:

.. _docker-node-context-class:

``DockerNodeContext`` class
---------------------------
.. autoclass:: vantage6.node.context.DockerNodeContext
   :members:

``DockerBaseManager`` class
---------------------------
.. autoclass:: vantage6.node.docker.docker_base.DockerBaseManager
   :members:

.. _docker-manager-class:

``DockerManager`` class
---------------------------
.. autoclass:: vantage6.node.docker.docker_manager.DockerManager
   :members:
   :show-inheritance:

.. autoclass:: vantage6.node.docker.docker_manager.Result

.. _task-manager-class:

``DockerTaskManager`` class
---------------------------
.. autoclass:: vantage6.node.docker.task_manager.DockerTaskManager
   :members:
   :show-inheritance:

.. _vpn-manager-class:

``VPNManager`` class
--------------------
.. autoclass:: vantage6.node.docker.vpn_manager.VPNManager
   :members:
   :show-inheritance:


Algorithm execution exceptions
-----------------
.. automodule:: vantage6.node.docker.exceptions
    :members:


Proxy server
------------

.. automodule:: vantage6.node.proxy_server
    :members:

.. _vnode-local-module:

``vnode-local`` commands
------------------------

.. automodule:: vantage6.node.cli.node

.. click:: vantage6.node.cli.node:cli_node
    :prog: vnode-local
    :nested: full
