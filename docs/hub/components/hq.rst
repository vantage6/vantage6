.. include:: <isonum.txt>

.. _hub-admin-guide-hq:

Headquarters
====

Vantage6 HQ is the central point of the vantage6 platform. It is responsible
for managing the organizations, nodes, collaborations, etc., and managing the
communication of task requests and results between the nodes and the users.

Communication with the vantage6 server is managed through a RESTful API and
socketIO server.

.. _hq-configure:

Configure
---------

Vantage6 HQ requires a configuration file to run. This is a ``yaml`` file with a
specific format, designed to be used with the vantage6 HQ Helm chart.
:ref:`This section <use-hub>` will help you to create a basic configuration file, but
will not cover all possible configuration options, as that would make a basic setup too
complex.

Below, we list all possible configuration options. You can download this file here:
:download:`hq_config.yaml <yaml/hq_config.yaml>`

.. _hq-configuration-file:

.. literalinclude :: yaml/hq_config.yaml
    :language: yaml

Where is my configuration file?
"""""""""""""""""""""""""""""""

To see where your configuration file is located, you can use the following
command

.. code:: bash

    v6 hq files

.. warning::
    This command will only work for if HQ has been deployed using the ``v6`` commands.

The directory where to store the configuration file depends on your
operating system (OS). It is possible to store the configuration file at
**system** or at **user** level. At the user level, configuration files are only
available for your user. By default, HQ configuration files are stored at
**system** level - except if you have created a sandbox environment using the
``v6 sandbox`` commands.

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

.. |win_sys| replace:: ``C:\ProgramData\vantage\hq``
.. |win_usr| replace:: ``C:\Users\<user>\AppData\Local\vantage\hq``
.. |mac_sys| replace:: ``/Library/Application/Support/vantage6/hq``
.. |mac_usr| replace:: ``/Users/<user>/Library/Application Support/vantage6/hq``
.. |lin_sys| replace:: ``/etc/xdg/vantage6/hq/``
.. |lin_usr| replace:: ``/home/<user>/.config/vantage6/hq/``

.. warning::
    The command ``v6 hq`` looks in certain directories by default. It is
    possible to use any directory and specify the location with the ``--config``
    flag. However, note that using a different directory requires you to specify
    the ``--config`` flag every time!

    Similarly, you can put your HQ configuration file in the user folder
    by using the ``--user`` flag. Note that in that case, you have to specify
    the ``--user`` flag for all ``v6 hq`` commands.


Permission management
---------------------

Almost everything in vantage6 HQ is under role-based access control: not
everyone is allowed to access everything.

There are three types of entities that can attempt to use vantage6 HQ: users,
nodes and algorithm containers. Not every resource is available to all three
entities. For example, only users can create new users or
organizations, and only nodes are allowed to update the results of a task
(the algorithm itself cannot do this as it exits when it finishes, and users
are not allowed to meddle with results).

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
   allow a user to view their own user details. Note that this figure may become
   outdated - however, the principles remain the same.

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

  When you create a new hub, the first time it is started, a new user 'admin'
  is created that has all permissions. This user should be used to create
  the first users and organizations.

To make it easier to assign permissions to users, there are roles. A role is
simply a set of rules. When a user is assigned a role, they are assigned all
the rules that are part of that role.

The permission structure of vantage6 allows for a lot of flexibility. However,
especially for beginning users, it can be a bit daunting to set up all the
permissions. Therefore, there are some default roles that can be used to quickly
set up a hub. These roles are, in descending order of permissions:

* Root: all permissions
* Collaboration Admin: can do almost everything for all organizations in
  collaborations that they are a member of, e.g. create new users but not
  delete the entire collaboration
* Organization Admin: can do everything for their own organization
* Researcher: can view the organization's resources and create tasks
* Viewer: can only view the organization's resources

We do recommend that you review the permissions of these roles before using them
in your own project.
