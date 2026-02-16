.. _python-client:

Python client
-------------

The Python client is the recommended way to interact with the vantage6 hub
for tasks that you want to automate. It is a Python library that facilitates
communication with the vantage6 hub, e.g. by encrypting and decrypting data
for tasks for you. It can create computation tasks and collect their
results, manage organizations, collaborations, users, etc. Everything you can do
with the UI, you can also do with the Python client, making it a powerful tool for
automation.

Requirements
^^^^^^^^^^^^

You need Python to use the Python client. We recommend using Python 3.13, as
the client has been tested with this version. For higher versions, it may be
difficult to install the dependencies.

.. warning::
    If you use vantage6 version 4, you should use Python 3.10 instead of Python 3.13.

Install
^^^^^^^

It is important to install the Python client with the same version as the
vantage6 hub you are talking to, most importantly the API version of vantage6 HQ. Check
your HQ version by going to
``https://<my-v6-HQ>/version`` (e.g. ``http://localhost:30761/hq/version``) to find its version.

Then you can install the ``vantage6-client`` with:

::

   # install the latest version
   uv pip install vantage6-client

   # install a specific version
   uv pip install vantage6-client==<version>

   # or, if you are using conda / pyenv / ...
   pip install vantage6==<version>

.. _use-python-client:

Use
^^^

First, we give an overview of the client. From the section :ref:`authentication`
onwards, there is example code of how to login with the client, and then
create organizations, tasks etc.

Overview
""""""""

The Python client contains groups of commands per resource type. For example,
the group ``client.user`` has the following commands:

- ``client.user.list()``: list all users
- ``client.user.create(username, password, ...)``: create a new user
- ``client.user.delete(<id>)``: delete a user
- ``client.user.get(<id>)``: get a user

You can see how to use these methods by using ``help(...)`` , e.g.
``help(client.role.create)`` will show you the parameters needed to create a
new role:

.. code:: python

   help(client.role.create)
   # Register new role
   #
   # Parameters
   # ----------
   # name : str
   #     Role name
   # description : str
   #     Human readable description of the role.
   # rules : list
   #     Rules that this role contains.
   # organization : int, optional
   #     Organization to which this role belongs. In case this is
   #     not provided the users organization is used. By default
   #     None.
   # field: str, optional
   #     Which data field to keep in the returned dict. For instance,
   #     "field='name'" will only return the name of the role. Default is None.
   # fields: list[str], optional
   #     Which data fields to keep in the returned dict. For instance,
   #     "fields=['name', 'id']" will only return the names and ids of the
   #     role. Default is None.
   #
   # Returns
   # -------
   # dict
   #     Containing meta-data of the new role


The following groups (related to the :ref:`components`) of methods are
available. They usually have ``list()``, ``create()``, ``delete()``
and ``get()`` methods attached - except where they are not relevant (for
example, a rule that gives a certain permission cannot be deleted).

-  ``client.user``
-  ``client.organization``
-  ``client.rule``
-  ``client.role``
-  ``client.collaboration``
-  ``client.task``
-  ``client.run``
-  ``client.result``
-  ``client.node``

Finally, the class ``client.util`` contains some utility functions, for example
to check if HQ is up and running or to change your own password.

.. _authentication:

Authentication
""""""""""""""

This section and the following sections introduce some minimal examples for
administrative tasks that you can perform with our
:ref:`Python client <use-python-client>`. We start by authenticating.

To authenticate, we create a config file to store our login information.
We do this so we do not have to define the ``hq_url``, ``auth_url`` and so on every
time we want to use the client. Moreover, it enables us to separate the sensitive
information (login details, organization key) that you do not want to make publicly
available, from other parts of the code you might write later (e.g. on
submitting particular tasks) that you might want to share publicly.

.. code:: python

   # config.py

   # HQ address, e.g. https://uluru.vantage6.ai/api, or http://localhost:7601/hq
   # for a local sandbox HQ
   hq_url = "https://<my_hq_url>:<my_port>/<my_api_path>"
   # Authentication service address, e.g. https://auth.uluru.vantage6.ai/, or
   # http://localhost:30764 for a local sandbox auth service
   auth_url = "https://<my_auth_url>:<my_port>"

   # If your collaboration is encrypted, you need to provide the filepath to the private
   # key of your organization. If your collaboration is not encrypted, you can leave this
   # as None.
   organization_key = None

   # Normally, these are not needed, unless your server admin has configured them
   # to non-default values
   keycloak_realm = "vantage6"
   keycloak_client = "public_client"


Then, we connect to the vantage6 hub by initializing a Client
object, and authenticating

.. code:: python

   from vantage6.client import UserClient as Client

   # Note: we assume here the config.py you just created is in the current directory.
   # If it is not, then you need to make sure it can be found on your PYTHONPATH
   import config

   # Initialize the client object, and run the authentication
   client = Client(
       hq_url=config.hq_url,
       auth_url=config.auth_url,
       auth_realm=config.keycloak_realm,
       auth_client=config.keycloak_client,
       log_level='debug'
   )
   client.authenticate()

   # Optional: setup the encryption, if you have an organization_key
   client.setup_encryption(config.organization_key)

.. note::

   If you are using a service account, the authentication process is a bit different:

   .. code:: python

      # instead of client.authenticate(), you need to initialize the service account
      # and then authenticate with it
      client.initialize_service_account(
         client_secret="<my-client-secret>",
         username="<my-username>"
      )
      client.authenticate_service_account()

   You get the client secret in a downloaded file when you create a service account in
   the User Interface. If you create a service account via the Python client or API,
   the client secret is returned in the JSON response.

.. _creating-organization:

Creating an organization
""""""""""""""""""""""""

After you have authenticated, you can start generating resources. The following
also assumes that you have a login on the vantage6 hub that has the
permissions to create a new organization. Regular end-users typically do
not have these permissions (typically only administrators do); they may skip
this part.

The first (optional, but recommended) step is to create an RSA keypair.
A keypair, consisting of a private and a public key, can be used to
encrypt data transfers. Users from the organization you are about to
create will only be able to use encryption if such a keypair has been
set up and if they have access to the private key.

.. code:: python

   from vantage6.common import warning, error, info, debug, bytes_to_base64s
   from vantage6.client.encryption import RSACryptor
   from pathlib import Path

   # Generated a new private key
   # Note that the file below doesn't exist yet: you will create it
   private_key_filepath = r'/path/to/private/key'
   private_key = RSACryptor.create_new_rsa_key(Path(private_key_filepath))

   # Generate the public key based on the private one
   public_key_bytes = RSACryptor.create_public_key_bytes(private_key)
   public_key = bytes_to_base64s(public_key_bytes)

Now, we can create an organization

.. code:: python

   client.organization.create(
       name = 'The_Shire',
       address1 = '501 Buckland Road',
       address2 = 'Matamata',
       zipcode = '3472',
       country = 'New Zealand',
       domain = 'the_shire.org',
       public_key = public_key   # use None if you haven't set up encryption or simply leave it out
   )

Users can now be created for this organization. Any users that are
created and who have access to the private key we generated above can
now use encryption by running

.. code:: python

   client.setup_encryption('/path/to/private/key')

after they authenticate.

Creating a collaboration
""""""""""""""""""""""""

Here, we assume that you have a Python session with an authenticated
Client object, as created in :ref:`authentication`. We
also assume that you have a login on the vantage6 hub that has the
permissions to create a new collaboration (regular end-users typically
do not have these permissions, this is typically only for
administrators).

A collaboration is an association of multiple
organizations that want to run analyses together.
First, you will need to find the organization id's of the organizations
you want to be part of the collaboration.

.. code:: python

   client.organization.list(fields=['id', 'name'])

Once you know the id's of the organizations you want in the
collaboration (e.g. 1 and 2), you can create the collaboration:

.. code:: python

   collaboration_name = "fictional_collab"
   organization_ids = [1,2] # the id's of the respective organizations
   client.collaboration.create(name = collaboration_name,
                               organizations = organization_ids,
                               encrypted = True)

Note that a collaboration can require participating organizations to use
encryption, by passing the ``encrypted = True`` argument (as we did
above) when creating the collaboration. It is recommended to do so, but
requires that a keypair was created when :ref:`creating-organization`
and that each user of that
organization has access to the private key so that they can run the
``client.setup_encryption(...)`` command after
:ref:`authentication`.

.. _register-node:

Registering a node
""""""""""""""""""

Here, we again assume that you have a Python session with an authenticated
Client object, as created in :ref:`authentication`, and that you have a login
that has the permissions to create a new node (regular end-users typically do not
have these permissions, this is typically only for administrators).

A node is associated with both a collaboration and an organization (see
:ref:`components`). You will need to find
the collaboration and organization id's for the node you want to
register:

.. code:: python

   client.organization.list(fields=['id', 'name'])
   client.collaboration.list(fields=['id', 'name'])

Then, we register a node with the desired organization and
collaboration. In this example, we create a node for the organization
with id 1 and collaboration with id 1.

.. code:: python

   # A node is associated with both a collaboration and an organization
   organization_id = 1
   collaboration_id = 1
   api_key = client.node.create(collaboration = collaboration_id, organization = organization_id)
   print(f"Registered a node for collaboration with id {collaboration_id}, organization with id {organization_id}. The API key that was generated for this node was {api_key}")

Remember to save the ``api_key`` that is returned here, since you will
need it when you :ref:`configure-node` the node.

Creating a task
"""""""""""""""

**Preliminaries**

Here we assume that

-  you have a Python session with an authenticated Client object, as
   created in :ref:`authentication`.
-  you already have the algorithm you want to run available as a
   container in a container registry (see
   `here <https://vantage6.discourse.group/t/developing-a-new-algorithm/31>`__
   for more details on developing your own algorithm)
-  the nodes are configured to look at the right database

In this manual, we'll use the averaging algorithm from
``harbor2.vantage6.ai/demo/average``, so the second requirement is met.
We'll assume the nodes in your collaboration have been configured to look as
something like:

.. code:: yaml

     databases:
       fileBased:
       - name: olympic_athletes_db
         uri: /my/local/path/to/data/olympic_athletes_2016.csv
         type: csv
         volumePath: /my/local/path/to/data
         originalName: olympic_athletes_2016.csv

The third requirement is met when all nodes have the same labels in their
configuration. As an end-user running the
algorithm, you'll need to align with the node owner about which database
name is used for the database you are interested in. For more details, see
:ref:`how to configure <configure-node>` your node.

**Determining which collaboration / organizations to create a task for**

First, you'll want to determine which collaboration to submit this task
to. To list all collaborations (that you have access to), run:

.. code:: python

   >>> client.collaboration.list(fields=['id', 'name'])
   [
    {
      'id': 1,
      'name': 'example_collab1',
    }
   ]

In this example, we see that there is only one collaboration called ``example_collab1``,
which has the id ``1``. To find out which organizations are associated with
collaboration ``1``, run:

.. code:: python

   >>> client.organization.list(collaboration=1, fields=['id', 'name'])
   [
      {'id': 2, 'name': 'example_org1'},
      {'id': 3, 'name': 'example_org2'},
      {'id': 4, 'name': 'example_org3'}
   ]

Now we see that this collaboration has three organizations associated with it, of which
the organization id's are ``2``, ``3`` and ``4``.

**Creating a session and extracting data from a database**

First, we need to create a session. A session is a collection of tasks that are related to each other.
For example, a session can be used to run a study, or a campaign.

.. code:: python

   session = client.session.create(
      name="my_session",
      collaboration=1
      scope="collaboration",
      display=True
   )

This will create a session with the name "my_session" and the scope "collaboration",
which means that it will be available to everyone in the collaboration.

Next, we need to extract data from a database. We can do this by creating a dataframe.

.. code:: python

   dataframe = client.dataframe.create(
      label="olympic_athletes_db",
      method="read_csv",
      image="harbor2.vantage6.ai/demo/average",
      arguments={},
      session=session["id"]
   )
   extraction_results = client.wait_for_results(dataframe["last_session_task"]["id"])

This will create a database extraction task that will yield a dataframe. Note that your
extraction method should match the database type you are using. The ``read_csv`` method
will only work for CSV files. For a SQL database, you might want to create a task like:

.. code:: python

   dataframe = client.dataframe.create(
      label="my_database",
      method="read_sql_database",
      image="harbor2.vantage6.ai/demo/average",
      arguments={"query": "SELECT * FROM my_table"},
      session=session["id"]
   )

:ref:`This section <algo-functions-provided>` provides more information on the available
data extraction methods.

.. _pyclient-create-task:

**Creating a task that runs the central algorithm**

Now, we have two options: create a task that will run the central part of an
algorithm (which runs on one node and may spawns subtasks on other nodes),
or create a task that will (only) run the partial methods (which are run
on each node). Typically, the partial methods only run the node local analysis
(e.g. compute the averages per node), whereas the central methods
performs aggregation of those results as well (e.g. starts the partial
analyses and then computes the overall average). First, let
us create a task that runs the central part of the
``harbor2.vantage6.ai/demo/average`` algorithm:

.. code:: python

   arguments = {
       'column_name': 'age'
   }

   average_task = client.task.create(
      collaboration=1,
      organizations=[2],
      name="an-awesome-task",
      image="harbor2.vantage6.ai/demo/average",
      description='',
      method='central_average',
      arguments=arguments,
      session=1,
      databases=[
         {'dataframe_id': dataframe["id"]}
      ],
      action="central_compute"
   )

Note that the ``arguments`` we defined are specific to
this algorithm: this algorithm expects an argument ``column_name`` to be
defined, and will compute the average over the column with that name.
Furthermore, note that here we created a task for collaboration with id
``1`` (i.e. our ``example_collab1``) and the organization with id ``2``
(i.e. ``example_org1``). I.e. the algorithm need not necessarily be run on *all* the
organizations involved in the collaboration. if you run the central task as in the
example above, it is even very common to only run it on one organization: the central
part usually creates subtasks that may run on multiple organizations.

**Creating a task that runs the partial algorithm**

You might be interested to know output of the partial algorithm (in this
example: the averages for the 'age' column for each node). In that case,
you can run only the partial algorithm, omitting the aggregation that the
central part of the algorithm will normally do:

.. code:: python

   arguments = {
       'column_name': 'age'
   }

   average_task = client.task.create(
      collaboration=1,
      organizations=[2,3],
      name="an-awesome-task",
      image="harbor2.vantage6.ai/demo/average",
      description='',
      method='partial_average',
      arguments=arguments,
      session=1,
      databases=[
         {'dataframe_id': dataframe["id"]}
      ],
      action="federated_compute"
   )

Note that when running the partial algorithm, you should run it on all organizations
that you want to get the results from. In this example, we run the partial algorithm
on both organizations ``2`` and ``3``.

**Inspecting the results**

Of course, it will take a little while to run your algorithm. You can use the following
code snippet to run a loop that checks HQ every 3 seconds to see if the task has been
completed:

.. code:: python

   print("Waiting for results")
   task_id = average_task['id']
   result = client.wait_for_results(task_id)

You can also check the status of the task using:

.. code:: python

   task_info = client.task.get(task_id, include_results=True)

and then retrieve the results

.. code:: python

   result_info = client.result.from_task(task_id=task_id)

The number of results may be different depending on what you run, but
for the central average algorithm in this example, the results would be:

.. code:: python

   >>> result_info
   [{'average': 53.25}]

while for the partial algorithms, dispatched to two nodes, the results would be:

.. code:: python

   >>> result_info
   [{'sum': 253, 'count': 4}, {'sum': 173, 'count': 4}]
