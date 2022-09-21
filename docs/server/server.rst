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

Items left
----------
* API design
* HATEOS
* Serialization
* RBAC
* background tasks
* Database
* Models / structure
* Relation to other components
* SocketIO connection
* RabbitMQ
* VPN server
* CLI (vserver local)

