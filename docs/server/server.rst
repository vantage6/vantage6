Server
======

Overview
--------

The two main roles of the central server in vantage6 are to provide an interface
with which the user can communicate with the data and to handle administrative
tasks such as user management and authentication.

Below we explain the implementation of the components that make up the server.

API
---

The API has a number of endpoints, for which GET, POST, PATCH and DELETE
requests have been implemented whenever they were required.

The server API is implemented in Flask, a web framework for Python.

.. .. automodule:: vantage6.server.resource
..    :members:

Role-based access control
+++++++++++++++++++++++++

Almost every endpoint on the API is under role-based access control: not
everyone and everything is allowed to access it.

There are three types of entities that can attempt to access the API: users,
nodes and algorithm containers. Not every endpoint is available to all three
entities. Therefore, there are decorators such as:

* ``@only_for(['user', 'container']``: only accessible for users and algorithm
  containers
* ``@with_user``: only users have access to this endpoint

These decorators ensure that only authenticated entities of the right type can
enter the endpoint.

When an endpoint is then entered, there are additional permission checks. For
users, permissions vary per user. Nodes and algorithm containers all have the
same permissions, but for specific situations there are specific checks. For
instance, nodes are only allowed to update their own results, and not those of
other nodes. These checks are performed within the endpoints themselves.

The following rules are defined:

.. figure:: /images/rules-overview.png
   :alt: Rule overview
   :align: center

   The rules that are available per resource, scope, and operation. For example,
   the first rule with resource 'User', scope 'Own' and operation 'View' will
   allow a user to view their own user details.

The rules have an operation, a scope, and a resource that they work on. For
instance, a rule with operation 'View', scope 'Organization' and resource
'Task', will allow a user to view all tasks of their own organization. There
are 4 operations (view, edit, create and delete) that correspond to GET, PATCH,
CREATE and DELETE requests, respectively. The scopes are:

* Global: all resources of all organizations
* Organization: resources of the user's own organization
* Collaboration: resources of all organizations that the user's organization is
  in a collaboration with
* Own: these are specific to the user endpoint. Permits a user to see/edit their
  own user, but not others within the organization.

API documentation
-----------------

We use OAS3+ for API documentation. This is already described in the section :ref:`oas3`.

Response structure (HATEOAS)
----------------------------
Each API endpoint returns a JSON response. All responses are structured in the
same way, according to the HATEOAS constraints. An example is detailed below:
::

  >>> client.task.get(task_id)
  {
      "id": 1,
      "name": "test",
      "results": [
          {
              "id": 2,
              "link": "/api/result/2",
              "methods": [
                  "PATCH",
                  "GET"
              ]
          }
      ],
      "image": "harbor2.vantage6.ai/testing/v6-test-py",
      ...
  }

The response for this task includes the results that are attached to this task.
In compliance with HATEOAS, a link is supplied to the link where the result can
be viewed in more detail.

Serialization
-------------

Relation to other components
----------------------------

Connection to node
++++++++++++++++++

The server is connected to the node(s) via a Websocket connection, which is a
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

VPN Server
++++++++++

The VPN server is an optional component of the vantage6 infrastructure that
allows algorithms running on different nodes to communicate with one another.
Its implementation is discussed at length in this `paper <https://ebooks.iospress.nl/pdf/doi/10.3233/SHTI220682>`_
and you can find information on how to set it up in our `user documentation <https://docs.vantage6.ai/installation/server/eduvpn>`_.

Now, when is the VPN server useful? The VPN server allows each node to establish
a VPN connection to the VPN server. The algorithm containers can use the VPN connection to communicate
with algorithm containers running on other nodes (provided those nodes have also
established a VPN connection). For each algorithm, the VPN IP address and one
or more ports with labels are stored in the database, which allows other
algorithm containers to find their contact details. This finally allows
algorithms to exchange information quickly without the need to go through the
central server for all communication.

.. todo::
  I guess this is documented elsewhere? Or it should be documented somewhere
  where algorithm building is discussed.




RabbitMQ
++++++++

Another optional component of the vantage6 infrastructure is a
`RabbitMQ server <https://https://www.rabbitmq.com/>`_. RabbitMQ is a widely
used message broker that we use to enable horizontal scaling (i.e. using more
than one instance) of the vantage6 server. Horizontal scaling is useful if
you have a high workload on your vantage6 server where a single server is node
longer sufficient. Below, we will first explain what we use RabbitMQ for, and
then discuss the implementation.

The websocket connection between server and nodes is used to process various
changes in the network's state. For example, a node can create a new (sub)task
for the other nodes in the collaboration. The server then communicates these
tasks via the socket connection. Now, if we use multiple instances of the
central server, different nodes in the same collaboration may connect to
different instances, and then, the server would not be able to deliver the new
task properly. This is where RabbitMQ comes in.

When RabbitMQ is enabled, the websocket messages are directed over the RabbitMQ
message queue, and delivered to the nodes regardless of which server instance
they are connected to. The RabbitMQ service thus helps to ensure that all
websocket events are still communicated properly to all involved parties.

If you use multiple server instances, you should always connect them to the same
RabbitMQ instance. You can achieve this by adding your RabbitMQ server when you
create a new server with :code:`vserver new`, or you can add it later to your
server configuration file with the flag :code:`rabbitmq_uri: <your URI>`.

A RabbitMQ URI is set up in the following way:

::

  amqp://$user:$password@$host:$port/$vhost

Where :code:`user` is the username, :code:`password` is the password,
:code:`host` is the URL where your RabbitMQ service is running, :code:`port` is
the queue's port (which is 5672 if you are using the RabbitMQ Docker image), and
:code:`vhost` is the name of your
`virtual host <https://www.rabbitmq.com/vhosts.html>`_ (you could e.g. run one
instance group per vhost).

We can recommend running the `Docker implementation <https://hub.docker.com/_/rabbitmq>`_
of RabbitMQ. It also ships a 'management' container that gives you a user
interface to manage your connections on port 15672.


Items left
----------
* API design
* HATEOS
* Serialization
* background tasks
* Database
* Models / structure
* Relation to other components
* VPN server
* CLI (vserver local)

