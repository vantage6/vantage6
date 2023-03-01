Socket connection
------------------

The server is connected to the node(s) via a SocketIO connection, which is a
bidirectional, peristent (event-based) communication line. We use the
Flask-SocketIO on the server side and python-socketio on the node (client) side.

Using the websocket connection goes as follows. If you want to send a message
from the server to the node, you can do something like:

::

  emit('message', 'some message', room='some_room')

which can be picked up by the node by a function like:

::

  class NodeTaskNamespace(ClientNamespace):
      def on_message(self, message):
          self.log.info(message)

.. TODO add that user can also connect. And what it's used for, etc