.. _server-shell:

Shell
"""""

.. warning::
    **Using the server shell is not recommended.** The shell is outdated and
    superseded by other tools. The shell offers a server admin the ability to
    manage the server entities, but does not offer any validation of the input.
    Therefore, it is easy to break the server by using the shell.

    Instead, we recommend using the :ref:`user interface <ui>`, the
    :ref:`Python client <python-client>` or the :ref:`API <server-api>`.

The shell allows a server admin to manage all server entities. To start
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

   # get the runs of all these tasks
   runs = organization.runs

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
the task is intended for, a corresponding (initially empty) run
should be created. Each task can have multiple runs, for example a
run from each organization.

.. code:: python

   # obtain organization from which this task is posted
   iknl = db.Organization.get_by_name("IKNL")

   # obtain collaboration for which we want to create a task
   collaboration = db.Collaboration.get(1)

   # obtain the next job_id. Tasks sharing the same job_id
   # can share the temporary volumes at the nodes. Usually this
   # job_id is assigned through the API (as the user is not allowed
   # to do so). All tasks from a master-container share the
   # same job_id
   job_id = db.Task.next_job_id()

   task = db.Task(
       name="some-name",
       description="some human readable description",
       image="docker-registry.org/image-name",
       collaboration=collaboration,
       job_id=job_id,
       database="default",
       init_org=iknl,
   )
   task.save()

   # input the algorithm container (docker-registry.org/image-name)
   # expects
   input_ = {
   }

   import datetime

   # now create a Run model for each organization within the
   # collaboration. This could also be a subset
   for org in collaboration.organizations:
       res = db.Run(
           input=input_,
           organization=org,
           task=task,
           assigned_at=datetime.datetime.now()
       )
       res.save()

Tasks can have a child/parent relationship. Note that the ``job_id`` is
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
       job_id=parent_task.job_id,
       database="default",
       init_org=iknl,
       parent=parent_task
   )
   child_task.save()

.. note::
    Tasks that share a ``job_id`` have access to the same temporary folder at
    the node. This allows for multi-stage algorithms.

Obtaining algorithm Runs:

.. code:: python

   # obtain all Runs
   db.Run.get()

   # obtain only completed runs
   [run for run in db.Run.get() if run.complete]

   # obtain run by its unique id
   db.Run.get(1)

