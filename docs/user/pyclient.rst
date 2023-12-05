.. _python-client:

Python client
-------------

The Python client is the recommended way to interact with the vantage6 server
for tasks that you want to automate. It is a Python library that facilitates
communication with the vantage6 server, e.g. by encrypting and decrypting data
for tasks for you.

The Python client aims to completely cover the vantage6 server communication.
It can create computation tasks and collect their
results, manage organizations, collaborations, users, etc. Under the hood,
the Python client talks to the server API to achieve this.

Requirements
^^^^^^^^^^^^

You need Python to use the Python client. We recommend using Python 3.10, as
the client has been tested with this version. For higher versions, it may be
difficult to install the dependencies.

.. warning::
    If you use a vantage6 version older than 3.8.0, you should use Python 3.7
    instead of Python 3.10.

Install
^^^^^^^

It is important to install the Python client with the same version as the
vantage6 server you are talking to. Check your server version by going to
``https://<server_url>/version`` (e.g. `https://cotopaxi.vantage6.ai/version`
or `http://localhost:5000/api/version`) to find its version.

Then you can install the ``vantage6-client`` with:

::

   pip install vantage6==<version>

where you add the version you want to install. You may also leave out
the version to install the most recent version.

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
``help(client.task.create)`` will show you the parameters needed to create a
new user:

.. code:: python

   help(client.task.create)
   #Create a new task
   #
   #    Parameters
   #    ----------
   #    collaboration : int
   #        Id of the collaboration to which this task belongs
   #    organizations : list
   #        Organization ids (within the collaboration) which need
   #        to execute this task
   #    name : str
   #        Human readable name
   #    image : str
   #        Docker image name which contains the algorithm
   #    description : str
   #        Human readable description
   #    input : dict
   #        Algorithm input
   #    database: str, optional
   #        Name of the database to use. This should match the key
   #        in the node configuration files. If not specified the
   #        default database will be tried.
   #
   #    Returns
   #    -------
   #    dict
   #        Containing the task information


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
to check if the server is up and running or to change your own password.

.. _authentication:

Authentication
""""""""""""""

This section and the following sections introduce some minimal examples for
administrative tasks that you can perform with our
:ref:`Python client <use-python-client>`. We start by authenticating.

To authenticate, we create a config file to store our login information.
We do this so we do not have to define the ``server_url``,
``server_port`` and so on every time we want to use the client.
Moreover, it enables us to separate the sensitive information (login
details, organization key) that you do not want to make publicly
available, from other parts of the code you might write later (e.g. on
submitting particular tasks) that you might want to share publicly.

.. code:: python

   # config.py

   server_url = "https://MY VANTAGE6 SERVER" # e.g. https://cotopaxi.vantage6.ai or
                                             # http://localhost for a local dev server
   server_port = 443 # This is specified when you first created the server
   server_api = "" # This is specified when you first created the server

   username = "MY USERNAME"
   password = "MY PASSWORD"

   organization_key = "FILEPATH TO MY PRIVATE KEY" # This can be empty if you do not want to set up encryption

Note that the ``organization_key`` should be a filepath that points to
the private key that was generated when the organization to which your
login belongs was first created (see :ref:`creating-organization`).

Then, we connect to the vantage 6 server by initializing a Client
object, and authenticating

.. code:: python

   from vantage6.client import UserClient as Client

   # Note: we assume here the config.py you just created is in the current directory.
   # If it is not, then you need to make sure it can be found on your PYTHONPATH
   import config

   # Initialize the client object, and run the authentication
   client = Client(config.server_url, config.server_port, config.server_api,
                   log_level='debug')
   client.authenticate(config.username, config.password)

   # Optional: setup the encryption, if you have an organization_key
   client.setup_encryption(config.organization_key)

.. _creating-organization:

Creating an organization
""""""""""""""""""""""""

After you have authenticated, you can start generating resources. The following
also assumes that you have a login on the Vantage6 server that has the
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
       public_key = public_key   # use None if you haven't set up encryption
   )

Users can now be created for this organization. Any users that are
created and who have access to the private key we generated above can
now use encryption by running

.. code:: python

   client.setup_encryption('/path/to/private/key')
   # or, if you don't use encryption
   client.setup_encryption(None)

after they authenticate.

Creating a collaboration
""""""""""""""""""""""""

Here, we assume that you have a Python session with an authenticated
Client object, as created in :ref:`authentication`. We
also assume that you have a login on the Vantage6 server that has the
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
   container in a docker registry (see
   `here <https://vantage6.discourse.group/t/developing-a-new-algorithm/31>`__
   for more details on developing your own algorithm)
-  the nodes are configured to look at the right database

In this manual, we'll use the averaging algorithm from
``harbor2.vantage6.ai/demo/average``, so the second requirement is met.
We'll assume the nodes in your collaboration have been configured to look as
something like:

.. code:: yaml

     databases:
        - label: default
          uri: /path/to/my/example.csv
          type: csv
        - label: my_other_database
          uri: /path/to/my/example2.csv
          type: excel

The third requirement is met when all nodes have the same labels in their
configuration. As an end-user running the
algorithm, you'll need to align with the node owner about which database
name is used for the database you are interested in. For more details, see
:ref:`how to configure <configure-node>` your node.

**Determining which collaboration / organizations to create a task for**

First, you'll want to determine which collaboration to submit this task
to, and which organizations from this collaboration you want to be
involved in the analysis

.. code:: python

   >>> client.collaboration.list(fields=['id', 'name', 'organizations'])
   [
    {'id': 1, 'name': 'example_collab1',
    'organizations': [
        {'id': 2, 'link': '/api/organization/2', 'methods': ['GET', 'PATCH']},
        {'id': 3, 'link': '/api/organization/3', 'methods': ['GET', 'PATCH']},
        {'id': 4, 'link': '/api/organization/4', 'methods': ['GET', 'PATCH']}
    ]}
   ]

In this example, we see that the collaboration called ``example_collab1``
has three organizations associated with it, of which the organization
id's are ``2``, ``3`` and ``4``. To figure out the names of these
organizations, we run:

.. code:: python

   >>> client.organization.list(fields=['id', 'name'])
   [{'id': 1, 'name': 'root'}, {'id': 2, 'name': 'example_org1'},
    {'id': 3, 'name': 'example_org2'}, {'id': 4, 'name': 'example_org3'}]

i.e. this collaboration consists of the organizations ``example_org1``
(with id ``2``), ``example_org2`` (with id ``3``) and ``example_org3``
(with id ``4``).

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

   input_ = {
       'method': 'central_average',
       'kwargs': {'column_name': 'age'}
   }

   average_task = client.task.create(
      collaboration=1,
      organizations=[2,3],
      name="an-awesome-task",
      image="harbor2.vantage6.ai/demo/average",
      description='',
      input_=input_,
      databases=[
         {'label': 'default'}
      ]
   )

Note that the ``kwargs`` we specified in the ``input_`` are specific to
this algorithm: this algorithm expects an argument ``column_name`` to be
defined, and will compute the average over the column with that name.
Furthermore, note that here we created a task for collaboration with id
``1`` (i.e. our ``example_collab1``) and the organizations with id ``2``
and ``3`` (i.e. ``example_org1`` and ``example_org2``). I.e. the
algorithm need not necessarily be run on *all* the organizations
involved in the collaboration.

Finally, note that you should provide any
databases that you want to use via the ``databases`` argument. In the example
above, we use the ``default`` database; using the ``my_other_database`` database
can be done by simply specifying that label in the dictionary. If you have
a SQL, SPARQL or OMOP database, you should also provide a ``query`` argument,
e.g.

.. code:: python

   databases=[
      {'label': 'default', 'query': 'SELECT * FROM my_table'}
   ]

Similarly, you can define a ``sheet_name`` for Excel databases if you want to
read data from a specific worksheet. Check ``help(client.task.create)`` for
more information.

**Creating a task that runs the partial algorithm**

You might be interested to know output of the partial algorithm (in this
example: the averages for the 'age' column for each node). In that case,
you can run only the partial algorithm, omitting the aggregation that the
central part of the algorithm will normally do:

.. code:: python

   input_ = {
       'method': 'partial_average',
       'kwargs': {'column_name': 'age'},
   }

   average_task = client.task.create(collaboration=1,
                                     organizations=[2,3],
                                     name="an-awesome-task",
                                     image="harbor2.vantage6.ai/demo/average",
                                     description='',
                                     input_=input_)

**Inspecting the results**

Of course, it will take a little while to run your algorithm. You can
use the following code snippet to run a loop that checks the server
every 3 seconds to see if the task has been completed:

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

