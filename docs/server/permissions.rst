Permission management
---------------------

Almost everything in the vantage6 server is under role-based access control: not
everyone is allowed to access everything.

Authentication types
~~~~~~~~~~~~~~~~~~~~

There are three types of entities that can attempt to use the vantage6 server: users,
nodes and algorithm containers. Not every resource is available to all three
entities. In the vantage6 server code, this is ensured by using so-called
decorators that are placed on the API endpoints. These decorators check if the
entity that is trying to access the endpoint is allowed to do so. For example,
you may see the following decorators on an endpoint:

* ``@only_for(['user', 'container']``: only accessible to users and algorithm
  containers
* ``@with_user``: only accessible to users

These decorators ensure that only authenticated entities of the right type can
enter the endpoint. For example, only users can create new users or
organizations, and only nodes are allowed to update the results of a task
(the algorithm itself cannot do this as it exits when it finishes, and users
are not allowed to meddle with results).

Permission rules
~~~~~~~~~~~~~~~~

The fact that users are allowed to create new organizations, does not mean that
all users are allowed to do so. There are permission rules that determine what
every user is allowed to do. These rules are assigned to a user by another user.
A user that creates a new user is never allowed to give the new user more
permissions than they have themselves.

Nodes and algorithm containers all have the same permissions, but for specific
situations there are specific checks. For instance, nodes are only allowed to
update their own results, and not those of other nodes.

The following rules are defined:

.. figure:: /images/rules-overview.png
   :alt: Rule overview
   :align: center

   The rules that are available per resource, scope, and operation. For example,
   the first rule with resource 'User', scope 'Own' and operation 'View' will
   allow a user to view their own user details.

The rules have an operation, a scope, and a resource that they work on. For
instance, a rule with operation 'View', scope 'Organization' and resource
'Task', will allow a user to view all tasks of their own organization.

There are six operations (view, edit, create, delete, send and receive). The
first four correspond to GET, PATCH, CREATE and DELETE requests, respectively.
The last two allow users to send and receive data via socket events.
For example, sending events would allow them to kill tasks that are running on
a node.

The scopes are:

* Global: all resources of all organizations
* Organization: resources of the user's own organization
* Collaboration: resources of all organizations that the user's organization is
  in a collaboration with
* Own: these are specific to the user endpoint. Permits a user to see/edit their
  own user, but not others within the organization.

A user may be assigned anywhere between zero and all of the rules.

.. note::

  When you create a new server, the first time it is started, a new user 'root'
  is created that has all permissions. This user is meant to be used to create
  the first users and organizations.

Roles
~~~~~

To make it easier to assign permissions to users, there are roles. A role is
simply a set of rules. When a user is assigned a role, they are assigned all
the rules that are part of that role.

The permission structure of vantage6 allows for a lot of flexibility. However,
especially for beginning users, it can be a bit daunting to set up all the
permissions. Therefore, there are some default roles that can be used to quickly
set up a server. These roles are, in descending order of permissions:

* Root: all permissions
* Collaboration Admin: can do almost everything for all organizations in
  collaborations that they are a member of, e.g. create new users but not
  delete the entire collaboration
* Organization Admin: can do everything for their own organization
* Researcher: can view the organization's resources and create tasks
* Viewer: can only view the organization's resources

We do recommend that you review the permissions of these roles before using them
in your own project.