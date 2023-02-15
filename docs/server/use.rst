.. _use-server:

Use
---

This section explains which commands are available to manage your server. It
also explains how to set up a test server locally and how to manage resources
via an IPython shell.

Quick start
"""""""""""

To create a new server, run the command below. A menu will be started
that allows you to set up a server configuration file.

::

   vserver new

For more details, check out the :ref:`server-configure` section.

To run a server, execute the command below. The ``--attach`` flag will
copy log output to the console.

::

   vserver start --name <your_server> --attach

.. warning::
    When the server is run for the first time, the following user is created:

    -  username: root
    -  password: root

    It is recommended to change this password immediately.

Finally, a server can be stopped again with:

::

   vserver stop --name <your_server>

Available commands
""""""""""""""""""

The following commands are available in your environment. To see all the
options that are available per command use the ``--help`` flag,
e.g. ``vserver start --help``.

+----------------+-----------------------------------------------------+
| **Command**    | **Description**                                     |
+================+=====================================================+
| ``vserver      | Create a new server configuration file              |
| new``          |                                                     |
+----------------+-----------------------------------------------------+
| ``vserver      | Start a server                                      |
| start``        |                                                     |
+----------------+-----------------------------------------------------+
| ``vserver      | Stop a server                                       |
| stop``         |                                                     |
+----------------+-----------------------------------------------------+
| ``vserver      | List the files that a server is using               |
| files``        |                                                     |
+----------------+-----------------------------------------------------+
| ``vserver      | Show a server's logs in the current terminal        |
| attach``       |                                                     |
+----------------+-----------------------------------------------------+
| ``vserver      | List the available server instances                 |
| list``         |                                                     |
+----------------+-----------------------------------------------------+
| ``vserver      | Run a server instance python shell                  |
| shell``        |                                                     |
+----------------+-----------------------------------------------------+
| ``vserver      | Import server entities as a batch                   |
| import``       |                                                     |
+----------------+-----------------------------------------------------+
| ``vserver      | Shows the versions of all the components of the     |
| version``      | running server                                      |
+----------------+-----------------------------------------------------+

.. _use-server-local:

Local test setup
""""""""""""""""

If the nodes and the server run at the same machine, you have to make
sure that the node can reach the server.

**Windows and MacOS**

Setting the server IP to ``0.0.0.0`` makes the server reachable
at your localhost (this is also the case when the dockerized version
is used). In order for the node to reach this server, set the
``server_url`` setting to ``host.docker.internal``.

.. warning::
    On the **M1** mac the local server might not be reachable from
    your nodes as ``host.docker.internal`` does not seem to refer to the
    host machine. Reach out to us on Discourse for a solution if you need
    this!

**Linux**

You should bind the server to ``0.0.0.0``. In the node
configuration files, you can then use ``http://172.17.0.1``, assuming you use
the default docker network settings.

.. _server-import:

Batch import
""""""""""""

You can easily create a set of test users, organizations and collaborations by
using a batch import. To do this, use the
``vserver import /path/to/file.yaml`` command. An example ``yaml`` file is
provided below.

You can download this file :download:`here <yaml/batch_import.yaml>`.


.. raw:: html

   <details>
   <summary><a>Example batch import</a></summary>

.. literalinclude :: yaml/server_config.yaml
    :language: yaml

.. raw:: html

   </details>

.. warning::
    All users that are imported using ``vserver import`` receive the superuser
    role. We are looking into ways to also be able to import roles. For more
    background info refer to this
    `issue <https://github.com/vantage6/vantage6/issues/71>`__.



.. _server-shell:

Shell
"""""

.. warning::
    The preferred method of managing entities is using the API, instead of the
    shell interface. This because the API will perform validation of the input,
    whereas in the shell all inputs are accepted.

Through the shell it is possible to manage all server entities. To start
the shell, use ``vserver shell [options]``.

In the next sections the different database models that are available
are explained. You can retrieve any record and edit any property of it.
Every ``db.`` object has a ``help()`` method which prints some info on
what data is stored in it (e.g. ``db.Organization.help()``).

.. note::
    Don't forget to call ``.save()`` once you are done editing an object.

.. _shell-organization:

Organizations
^^^^^^^^^^^^^

.. note::
    Organizations have a public key that is used for end-to-end encryption.
    This key is automatically created and/or uploaded by the node the first
    time it runs.

To store an organization you can use the ``db.Organization`` model:

.. code:: python

   # create new organiztion
   organization = db.Organization(
       name="IKNL",
       domain="iknl.nl",
       address1="Zernikestraat 29",
       address2="Eindhoven",
       zipcode="5612HZ",
       country="Netherlands"
   )

   # store organization in the database
   organization.save()

Retrieving organizations from the database:

.. code:: python

   # get all organizations in the database
   organizations = db.Organization.get()

   # get organization by its unique id
   organization = db.Organization.get(1)

   # get organization by its name
   organization = db.Organization.get_by_name("IKNL")

A lot of entities (e.g. users) at the server are connected to an
organization. E.g. you can see which (computation) tasks are issued by
the organization or see which collaborations it is participating in.

.. code:: python

   # retrieve organization from which we want to know more
   organization = db.Organization.get_by_name("IKNL")

   # get all collaborations in which the organization participates
   collaborations = organization.collaborations

   # get all users from the organization
   users = organization.users

   # get all created tasks (from all users)
   tasks = organization.created_tasks

   # get the results of all these tasks
   results = organization.results

   # get all nodes of this organization (for each collaboration
   # an organization participates in, it needs a node)
   nodes = organization.nodes

Roles and Rules
^^^^^^^^^^^^^^^

A user can have multiple roles and rules assigned to them. These are
used to determine if the user has permission to view, edit, create or
delete certain resources using the API. A role is a collection of rules.

.. code:: bash

   # display all available rules
   db.Rule.get()

   # display rule 1
   db.Rule.get(1)

   # display all available roles
   db.Role.get()

   # display role 3
   db.Role.get(3)

   # show all rules that belong to role 3
   db.Role.get(3).rules

   # retrieve a certain rule from the DB
   rule = db.Rule.get_by_("node", Scope, Operation)

   # create a new role
   role = db.Role(name="role-name", rules=[rule])
   role.save()

   # or assign the rule directly to the user
   user = db.User.get_by_username("some-existing-username")
   user.rules.append(rule)
   user.save()

Users
^^^^^

Users belong to an organization. So if you have not created any
:ref:`shell-organization` yet, then you should do that first. To create a user
you can use the ``db.User`` model:

.. code:: python

   # first obtain the organization to which the new user belongs
   org = db.Organization.get_by_name("IKNL")

   # obtain role 3 to assign to the new user
   role_3 = db.Role.get(3)

   # create the new users, see section Roles and Rules on how to
   # deal with permissions
   new_user = db.User(
       username="root",
       password="super-secret",
       firstname="John",
       lastname="Doe",
       roles=[role_3],
       rules=[],
       organization=org
   )

   # store the user in the database
   new_user.save()

You can retrieve users in the following ways:

.. code:: python

   # get all users
   db.User.get()

   # get user 1
   db.User.get(1)

   # get user by username
   db.User.get_by_username("root")

   # get all users from the organization IKNL
   db.Organization.get_by_name("IKNL").users

To modify a user, simply adjust the properties and save the object.

.. code:: python

   user = db.User.get_by_username("some-existing-username")

   # update the firstname
   user.firstname = "Brandnew"

   # update the password; it is automatically hashed.
   user.password = "something-new"

   # store the updated user in the database
   user.save()

Collaborations
^^^^^^^^^^^^^^

A collaboration consists of one or more organizations. To create a
collaboration you need at least one but preferably multiple
:ref:`shell-organization` in your database. To create a
collaboration you can use the ``db.Collaboration`` model:

.. code:: python

   # create a second organization to collaborate with
   other_organization = db.Organization(
       name="IKNL",
       domain="iknl.nl",
       address1="Zernikestraat 29",
       address2="Eindhoven",
       zipcode="5612HZ",
       country="Netherlands"
   )
   other_organization.save()

   # get organization we have created earlier
   iknl = db.Organization.get_by_name("IKNL")

   # create the collaboration
   collaboration = db.Collaboration(
       name="collaboration-name",
       encrypted=False,
       organizations=[iknl, other_organization]
   )

   # store the collaboration in the database
   collaboration.save()

Tasks, nodes and organizations are directly related to collaborations.
We can obtain these by:

.. code:: python

   # obtain a collaboration which we like to inspect
   collaboration = db.Collaboration.get(1)

   # get all nodes
   collaboration.nodes

   # get all tasks issued for this collaboration
   collaboration.tasks

   # get all organizations
   collaboration.organizations

.. warning::
    Setting the encryption to False at the server does not mean that the nodes
    will send encrypted results. This is only the case if the nodes also agree
    on this setting. If they don't, you will receive an error message.

Nodes
^^^^^

Before nodes can login, they need to exist in the server's database. A
new node can be created as follows:

.. code:: python

   # we'll use a uuid as the API-key, but you can use anything as
   # API key
   from uuid import uuid1

   # nodes always belong to an organization *and* a collaboration,
   # this combination needs to be unique!
   iknl = db.Organization.get_by_name("IKNL")
   collab = iknl.collaborations[0]

   # generate and save
   api_key = str(uuid1())
   print(api_key)

   node = db.Node(
       name = f"IKNL Node - Collaboration {collab.name}",
       organization = iknl,
       collaboration = collab,
       api_key = api_key
   )

   # save the new node to the database
   node.save()

.. note::
    API keys are hashed before stored in the database. Therefore you need to
    save the API key immediately. If you lose it, you can reset the API key
    later via the shell, API, client or UI.

Tasks and Results
^^^^^^^^^^^^^^^^^

.. warning::
    Tasks(/results) created from the shell are not picked up by nodes that are
    already running. The signal to notify them of a new task cannot be emitted
    this way. We therefore recommend sending tasks via the Python client.

A task is intended for one or more organizations. For each organization
the task is intended for, a corresponding (initially empty) result
should be created. Each task can have multiple results, for example a
result from each organization.

.. code:: python

   # obtain organization from which this task is posted
   iknl = db.Organization.get_by_name("IKNL")

   # obtain collaboration for which we want to create a task
   collaboration = db.Collaboration.get(1)

   # obtain the next run_id. Tasks sharing the same run_id
   # can share the temporary volumes at the nodes. Usually this
   # run_id is assigned through the API (as the user is not allowed
   # to do so). All tasks from a master-container share the
   # same run_id
   run_id = db.Task.next_run_id()

   task = db.Task(
       name="some-name",
       description="some human readable description",
       image="docker-registry.org/image-name",
       collaboration=collaboration,
       run_id=run_id,
       database="default",
       initiator=iknl,
   )
   task.save()

   # input the algorithm container (docker-registry.org/image-name)
   # expects
   input_ = {
   }

   import datetime

   # now create a result model for each organization within the
   # collaboration. This could also be a subset
   for org in collaboration.organizations:
       res = db.Result(
           input=input_,
           organization=org,
           task=task,
           assigned_at=datetime.datetime.now()
       )
       res.save()

Tasks can have a child/parent relationship. Note that the ``run_id`` is
for parent and child tasks the same.

.. code:: python

   # get a task to which we want to create some
   # child tasks
   parent_task = db.Task.get(1)

   child_task = db.Task(
       name="some-name",
       description="some human readable description",
       image="docker-registry.org/image-name",
       collaboration=collaboration,
       run_id=parent_task.run_id,
       database="default",
       initiator=iknl,
       parent=parent_task
   )
   child_task.save()

.. note::
    Tasks that share a ``run_id`` have access to the same temporary folder at
    the node. This allows for multi-stage algorithms.

Obtaining results:

.. code:: python

   # obtain all Results
   db.Result.get()

   # obtain only completed results
   [result for result in db.Result.get() if result.complete]

   # obtain result by its unique id
   db.Result.get(1)

