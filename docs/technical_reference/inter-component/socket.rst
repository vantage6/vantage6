.. _socket:

SocketIO connection
-------------------

A `SocketIO connection <https://socket.io/docs/v4/>`_ is a bidirectional,
persistent, event-based communication line. In vantage6, it is used for example
to send status updates from HQ to the nodes or to send a signal to a
node that it should kill a task.

Each socketIO connection consists between HQ and one of the clients (nodes or users).
The clients can only send a message to HQ and not to each other. HQ
can send messages to all clients or to a specific client or group of clients.

.. note::

    The vantage6 user interface automatically establishes a socketIO connection with HQ
    when the user logs in. It will use the connection to update information shown in the
    UI.

Permissions
+++++++++++

The socketIO connection is split into different rooms. Vantage6 HQ
decides which rooms a client is allowed to join; they will only be able to read
messages from that room.

Nodes always join the room of their own collaboration, and a room of all nodes.
Users only join the room of collaborations whose events they are allowed to
view which is checked via event view rules.

Usage in vantage6
+++++++++++++++++

HQ sends the following events to the clients (nodes or users):

- Notify nodes a new task is available
- Letting nodes and users know if a node in their collaboration comes online or
  goes offline
- Instructing nodes to renew their token if it is expired
- Letting nodes and users know if a task changed state on a node (e.g. started,
  finished, failed). This is especially important for nodes to know in case
  an algorithm they are running depends on the output of another node.
- Instruct nodes to kill one or more tasks
- Checking if nodes are still online

The nodes send the following events to HQ:

- Alert HQ of task state changes (e.g. started, finished, failed)
- Share information about the node configuration (e.g. which algorithms are
  allowed to run on the node)

In theory, users could also use their socketIO connection to send events, but
none of the events they send will lead to action on HQ.

.. todo refer to API reference