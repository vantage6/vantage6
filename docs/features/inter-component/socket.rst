SocketIO connection
------------------

A `SocketIO connection <https://socket.io/docs/v4/>`_ is a bidirectional,
persistent, event-based communication line. In vantage6, it is used for example
to send status updates from the server to the nodes or to send a signal to a
node that it should kill a task.

Each socketIO connection consists of a server and one or more clients. The
clients can only send a message to the server and not to each other. The server
can send messages to all clients or to a specific client. In vantage6, the
central server is the socketIO server; the clients can be nodes or users.

.. note::
    The vantage6 user interface automatically establishes a socketIO connection
    with the server when the user logs in. The user can then view the updates
    they are allowed to see.

Permissions
+++++++++++

The socketIO connection is split into different rooms. The vantage6 server
decides which rooms a client is allowed to join; they will only be able to read
messages from that room.

Nodes always join the room of their own collaboration, and a room of all nodes.
Users only join the room of collaborations whose events they are allowed to
view which is checked via event view rules.

Usage in vantage6
+++++++++++++++++

The server sends the following events to the clients:

- Notify nodes a new task is available
- Letting nodes and users know if a node in their collaboration comes online or
  goes offline
- Instructing nodes to renew their token if it is expired
- Letting nodes and users know if a task changed state on a node (e.g. started,
  finished, failed). This is especially important for nodes to know in case
  an algorithm they are running depends on the output of another node.
- Instruct nodes to kill one or more tasks
- Checking if nodes are still alive

The nodes send the following events to the server:

- Alert the server of task state changes (e.g. started, finished, failed)
- Share information about the node configuration (e.g. which algorithms are
  allowed to run on the node)

In theory, users could use their socketIO connection to send events, but
none of the events they send will lead to action on the server.

.. todo refer to API reference