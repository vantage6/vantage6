.. include:: <isonum.txt>

.. _server-admin-guide-core:

Core
====

The vantage6 core is the central hub of the vantage6 platform. It is responsible
for managing the different organizations and their nodes, authorizing the users and
nodes, and managing the communication of task requests and results between the nodes
and the users.

Communication with the vantage6 core is managed through a RESTful API and
socketIO server.



.. _server-configure:

Configure
---------

The vantage6-server requires a configuration file to run. This is a
``yaml`` file with a specific format.

The next sections describes how to configure the server. It first provides a few
quick answers on setting up your server, then explains where your vantage6
configuration files are stored, and finally shows an example of all
configuration file options.

How to create a configuration file
""""""""""""""""""""""""""""""""""

The easiest way to create an initial
configuration file is via: ``v6 server new``. This allows you to configure the
basic settings. For more advanced configuration options, which are listed below,
you can view the :ref:`example configuration file <server-config-file-structure>`.


Where is my configuration file?
"""""""""""""""""""""""""""""""

To see where your configuration file is located, you can use the following
command

.. code:: bash

    v6 server files

.. warning::
    This command will only work for if the server has been deployed using the
    ``v6`` commands.

    Also, note that on local deployments you may need to specify the
    ``--user`` flag if you put your configuration file in the
    :ref:`user folder <server-configure-location>`.

You can also create and edit this file manually.

.. _server-config-file-structure:

All configuration options
"""""""""""""""""""""""""

The following configuration file is an example that intends to list all possible
configuration options.

You can download this file here: :download:`server_config.yaml <yaml/server_config.yaml>`

.. _server-configuration-file:

.. literalinclude :: yaml/server_config.yaml
    :language: yaml

.. todo this section is close duplicate of docs/node/configure -- merge?

.. _server-configure-location:

Configuration file location
"""""""""""""""""""""""""""

The directory where to store the configuration file depends on your
operating system (OS). It is possible to store the configuration file at
**system** or at **user** level. At the user level, configuration files are only
available for your user. By default, server configuration files are stored at
**system** level.

The default directories per OS are as follows:

+---------+----------------------------+------------------------------------+
| **OS**  | **System**                 | **User**                           |
+=========+============================+====================================+
| Windows | |win_sys|                  | |win_usr|                          |
+---------+----------------------------+------------------------------------+
| MacOS   | |mac_sys|                  | |mac_usr|                          |
+---------+----------------------------+------------------------------------+
| Linux   | |lin_sys|                  | |lin_usr|                          |
+---------+----------------------------+------------------------------------+

.. |win_sys| replace:: ``C:\ProgramData\vantage\server``
.. |win_usr| replace:: ``C:\Users\<user>\AppData\Local\vantage\server``
.. |mac_sys| replace:: ``/Library/Application/Support/vantage6/server``
.. |mac_usr| replace:: ``/Users/<user>/Library/Application Support/vantage6/server``
.. |lin_sys| replace:: ``/etc/xdg/vantage6/server/``
.. |lin_usr| replace:: ``/home/<user>/.config/vantage6/server/``

.. warning::
    The command ``v6 server`` looks in certain directories by default. It is
    possible to use any directory and specify the location with the ``--config``
    flag. However, note that using a different directory requires you to specify
    the ``--config`` flag every time!

    Similarly, you can put your server configuration file in the user folder
    by using the ``--user`` flag. Note that in that case, you have to specify
    the ``--user`` flag for all ``v6 server`` commands.


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

* ``@only_for(('user', 'container'))``: only accessible to users and algorithm
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





