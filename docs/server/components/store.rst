.. include:: <isonum.txt>

.. _server-admin-guide-store:

Store
=====

The vantage6 store is a component that stores the algorithms that can be used by the
nodes. This allows the user to easily find the algorithm they need, and know how to
use it.

.. tip::

   There is a community algorithm store hosted at
   `https://store.cotopaxi.vantage6.ai <https://store.cotopaxi.vantage6.ai>`_.
   This store is maintained by the vantage6 community and allows you to easily reuse
   algorithms developed by others. You can also create your own algorithm store. This
   allows you to create a private algorithm store, which is only available to your own
   collaborations.


Linking algorithm store to core
-------------------------------
Algorithm stores can be linked to a vantage6 server or to a specific collaboration on a
server. If an algorithm store is linked to a server, the algorithms in the store are
available to all collaborations on that server. If an algorithm store is linked to a
collaboration, the algorithms in the store are only available to that collaboration.

Users can link algorithm stores to a collaboration if they have permission to modify
that collaboration. Algorithm stores can only be linked to a server by users that have
permission to modify all collaborations on the server.

To link an algorithm store, go to the collaboration settings page on the UI or use the
Python client function ``client.store.create()``. When linking a store to a server, you
need to provide the algorithm store URL, a name to refer to the store, and the
collaboration ID of the collaboration you want to link the store to. Alternatively, you
can link a store to all collaborations on the server by not providing a collaboration
ID.

Store processes
---------------
The algorithm store manages the lifecycle of vantage6 algorithms, from its initial
submission by the algorithm developer to the running of the algorithm and finally its
replacement by a newer version. This page intends to give an overview of these processes.

Algorithm submission
^^^^^^^^^^^^^^^^^^^^

The first step in the lifecycle of an algorithm is its submission to the algorithm store.
An algorithm developer can do this via the algorithm store section of the UI or by using
the Python client's command ``client.algorithm.create()``. The algorithm developer needs
to provide data such as a name, description, where to find the code and the docker
image, and which functions the algorithm provides and how to call them.

Each function of the algorithm is described, apart from its name and description, by the
following fields:

- **Parameters**: A list of parameters that the function expects. Each parameter has a
  name, a description, and a type. For example, if you want to compute an average, a
  parameter could be a column name. Apart from standard data types like integers,
  strings and booleans, vantage6 also supports *organizations* and *columns* as parameter
  types. When using these types, the user interface knows to show a dropdown with the
  available organizations or columns.

- **Databases**: A list of databases that the function expects. Most algorithms use a
  single database, but some algorithms might need multiple databases (e.g. one with
  patient data and another with population data). Each database has a name
  and a description. The user interface will show a dropdown with the available databases
  when the user needs to select a database.

- **Visualizations**: A list of visualizations that the function can produce. Each
  visualization has a name, a description, and a type. When viewing the results of an
  algorithm run in the UI, the UI will attempt to plot the results if a visualization
  is available. Depending on the visualization type, additional data might be required.
  For instance, for a line graph, the algorithm developer can set the x-axis and y-axis
  columns that should be visualized.


Algorithm review
^^^^^^^^^^^^^^^^

After an algorithm is submitted, it needs to undergo a review process. First, one or
more reviewers have to be assigned. Depending on their permissions, the algorithm
developer can do this themselves or a store manager can assign reviewers. The reviewers
can then view the algorithm and provide feedback. If the algorithm is approved, it will
be shown as approved in the UI and can be used to run tasks. While the algorithm is
under review, it is not yet available for running tasks in the UI. If your algorithm
store has been configured with an email server, emails will be sent to alert users that,
for instance, their review is requested.

Regularly, a developer has submitted an update to an algorithm that was already
approved. In such cases, when the changes are approved, the algorithm store will
invalidate the previous version of the algorithm. This means that the previous version
can then no longer be used to run tasks. It is also possible to invalidate an algorithm
without superseding it with a new version. This can be useful if an algorithm is found
to be faulty or if it is no longer needed.

.. _algorithm-store-configure:

Configuration options
---------------------

The algorithm store requires a configuration file to run. This is a ``yaml`` file with
a specific format.

The next sections describes how to configure the algorithm store. It first provides a few
quick answers on setting up your store, then shows an example of all configuration file
options, and finally explains where your configuration files are stored.

How to create a configuration file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The easiest way to create an initial configuration file is via:
``v6 algorithm-store new``. This allows you to configure the
basic settings. For more advanced configuration options, which are listed below,
you can view the :ref:`example configuration file <algorithm-store-config-file-structure>`.


Where is my configuration file?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To see where your configuration file is located, you can use the following
command

.. code:: bash

    v6 algorithm-store files

.. warning::
    This command will only work for if the algorithm store has been deployed
    using the ``v6`` commands.

    Also, note that on local deployments you may need to specify the
    ``--user`` flag if you put your configuration file in the
    :ref:`user folder <algorithm-store-configure-location>`.

You can also create and edit this file manually.

.. _algorithm-store-config-file-structure:

All configuration options
^^^^^^^^^^^^^^^^^^^^^^^^^^

The following configuration file is an example that intends to list all possible
configuration options.

You can download this file here: :download:`algorithm_store_config.yaml <yaml/algorithm_store_config.yaml>`

.. _algorithm-store-configuration-file:

.. literalinclude :: yaml/algorithm_store_config.yaml
    :language: yaml

.. todo this section is close duplicate of docs/node/configure -- merge?

.. _algorithm-store-configure-location:

Configuration file location
^^^^^^^^^^^^^^^^^^^^^^^^^^^

The directory where to store the configuration file depends on your
operating system (OS). It is possible to store the configuration file at
**system** or at **user** level. At the user level, configuration files are only
available for your user. By default, algorithm store configuration files are
stored at **system** level.

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

.. |win_sys| replace:: ``C:\ProgramData\vantage\algorithm-store``
.. |win_usr| replace:: ``C:\Users\<user>\AppData\Local\vantage\algorithm-store``
.. |mac_sys| replace:: ``/Library/Application/Support/vantage6/algorithm-store``
.. |mac_usr| replace:: ``/Users/<user>/Library/Application Support/vantage6/algorithm-store``
.. |lin_sys| replace:: ``/etc/xdg/vantage6/algorithm-store/``
.. |lin_usr| replace:: ``/home/<user>/.config/vantage6/algorithm-store/``

.. warning::
    The command ``v6 algorithm-store`` looks in certain directories by default. It is
    possible to use any directory and specify the location with the ``--config``
    flag. However, note that using a different directory requires you to specify
    the ``--config`` flag every time!

    Similarly, you can put your algorithm store configuration file in the user folder
    by using the ``--user`` flag. Note that in that case, you have to specify
    the ``--user`` flag for all ``v6 algorithm-store`` commands.


Permissions
-----------

Policies
^^^^^^^^

Algorithm store policies are defined by the algorithm store administrator and determine
the general permission and access rules for the algorithm store. Arguably the most
important policy is who is allowed to view the algorithms in the store. For the
community store, this is set to public, meaning that anyone can view the algorithms. For
a private store, this can be set to private, meaning that only authorized users can
view the algorithms. Other policies can be set to define which vantage6 servers are
allowed to access the store, or to shape the review process (e.g. how many reviewers
are required, or if they should be from a different organization as the algorithm
developer).

Permission management
^^^^^^^^^^^^^^^^^^^^^^

The permission system of the algorithm store is based on a combination of policies and
rules. Policies are used to define general access rules from external entities (i.e.
users, vantage6 servers), while rules are used to determine the actions that a user is
allowed to take in the algorithm store. An example of a policy is a setting that anyone
has read-only access to the algorithm store even if they are not authenticated. An
example of a rule is that a certain user is given permission to submit new algorithms to
the store.

In order to perform operations in the algorithm store, a user must be registered in the
algorithm store and must be authenticated. A user account is linked to a whitelisted
vantage6 server, and the authentication is performed by logging in though the vantage6
server and using the obtained token to run a request on an algorithm store resource
endpoint.

Just like in the vantage6 server, in the algorithm store rules are used to allow or
prevent a user from performing an operation. An operation is an action that can be
performed on a resource of the algorithm store. The following operations are defined:

#. Create
#. Delete
#. Edit
#. View

These operations can be performed on the available resources according to the following schema:

.. list-table::
   :name: rules-algo-store
   :widths: 20 20 20 20 20

   * - Resource
     - View
     - Create
     - Edit
     - Delete
   * - Algorithm
     - ✅
     - ✅
     - ✅
     - ✅
   * - User
     - ✅
     - ✅
     - ✅
     - ✅
   * - Role
     - ✅
     - ✅
     - ✅
     - ✅
   * - Review
     - ✅
     - ✅
     - ✅
     - ✅
   * - Whitelisted server
     - N/A
     - N/A
     - N/A
     - ✅

Note that not some permissions are not defined, because they do not correspond to any
existing operation that requires permission.

Rules can be assigned to a user by another user who has at least the same permission level
as the rules assigned. Single rules can be assigned, but default combinations of rules
are available, as roles. The following default roles available in the algorithms store:

#. **Root**: Has all permissions.
#. **Developer**: Can submit new algorithms to the store and edit them before they are
   reviewed.
#. **Algorithm Manager**: Can assign reviewers to new algorithms, and manage
   algorithms. Whenever a new algorithm is submitted, users with permission to register
   new reviews are alerted, so users with this role as well as the root role will be
   alerted to assign reviewers (if an email server has been set up).
#. **Reviewer**: Can approve or reject algorithms that they have been requested to
   review.
#. **Viewer**: Can view all resources in the store.
#. **Store Manager**: Can manage the store's users and their permissions.
#. **Server Manager**: This role is automatically given to the user that whitelists
   their vantage6 server in the algorithm store. This role only gives them permission to
   undo the whitelisting of their server.

Note that all default roles have permission to view all resources. To give an example,
the permissions of a reviewer are shown below.

.. list-table::
   :name: rules-algo-store-reviewer
   :widths: 20 20 20 20 20

   * - Resource
     - View
     - Create
     - Edit
     - Delete
   * - Algorithm
     - ✅
     - ❌
     - ❌
     - ❌
   * - User
     - ✅
     - ❌
     - ❌
     - ❌
   * - Role
     - ✅
     - ❌
     - ❌
     - ❌
   * - Review
     - ✅
     - ❌
     - ✅
     - ❌
   * - Whitelisted server
     -
     -
     -
     - ❌
