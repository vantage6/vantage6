Permission management
---------------------

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