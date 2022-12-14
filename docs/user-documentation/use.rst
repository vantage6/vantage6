Use
===

Preliminaries
-------------

.. _concepts:

Concepts
^^^^^^^^

There are several entities in vantage6, such as users, organizations,
tasks, etc. The following statements should help you understand the
relationships.

-  A **collaboration** is a collection of one or more
   **organizations**.
-  For each collaboration, each participating organization needs a
   **node** to compute tasks.
-  Each organization can have **users** who can perform certain
   actions.
-  The permissions of the user are defined by the assigned **rules**.
-  It is possible to collect multiple rules into a **role**, which can
   also be assigned to a user.
-  Users can create **tasks** for one or more organizations within a
   collaboration.
-  A task should produce a **result** for each organization involved in
   the task.

The following schema is a *simplified* version of the database:

.. figure:: /images/db_model.png

   Simplified database model

End to end encryption
^^^^^^^^^^^^^^^^^^^^^

Encryption in vantage6 is handled at organization level. Whether
encryption is used or not, is set at collaboration level. All the nodes
in the collaboration need to agree on this setting. You can enable or
disable encryption in the node configuration file, see the example in
:ref:`node-configure-structure`.

.. figure:: /images/encryption.png

   Encryption takes place between organizations therefore all nodes and
   users from the a single organization should use the same private key.

The encryption module encrypts data so that the server is unable to read
communication between users and nodes. The only messages that go from
one organization to another through the server are computation requests
and their results. Only the algorithm input and output are encrypted.
Other metadata (e.g. time started, finished, etc), can be read by the
server.

The encryption module uses RSA keys. The public key is uploaded to the
vantage6-server. Tasks and other users can use this public key (this is
automatically handled by the python-client and R-client) to send
messages to the other parties.

.. note::
    The RSA key is used to create a shared secret which is used for encryption
    and decryption of the payload.

When the node starts, it checks that the public key stored at the server
is derived from the local private key. If this is not the case, the node
will replace the public key at the server.

.. warning::
    If an organization has multiple nodes and/or users, they must use the same
    private key.

In case you want to generate a new private key, you can use the command
``vnode create-private-key``. If a key already exists at the local
system, the existing key is reused (unless you use the ``--force``
flag). This way, it is easy to configure multiple nodes to use the same
key.

It is also possible to generate the key yourself and upload it by using the
endpoint ``https://SERVER[/api_path]/organization/<ID>``.

Client
------

Introduction
^^^^^^^^^^^^

We provide four ways in which you can interact with the server to manage
your vantage6 resources:

-  :ref:`use-client-ui`
-  :ref:`use-python-client`
-  :ref:`use-R-client`
-  :ref:`use-server-api`

The UI and the clients make it much easier to interact with the server
than directly interacting with the server API through HTTP requests,
especially as data is serialized and encrypted automatically. For most
use cases, we recommend to use the UI and/or the Python client.

.. note::
    The R client is only suitable for creating tasks and retrieve their results.
    With the Python client it is possible to use the entire API.

Note that whenever you interact with the server, you are limited by your
permissions. For instance, if you try to create another user but do not
have permission to do so, you will receive an error message. All
permissions are described by rules, which can be aggregated in roles.
Contact your server administrator if you find your permissions are
inappropriate.

.. note::
    There are predefined roles such as 'Researcher' and 'Organization Admin'
    that are automatically created by the server. These can be assigned to any
    new user by the administrator that is creating the user.

.. _use-client-ui:

User Interface
^^^^^^^^^^^^^^

The User Interface (UI) is a web application that aims to make it easy
to interact with the server. At present, it provides all functionality
except for creating tasks. We aim to incorporate this functionality in
the near future.

Using the UI should be relatively straightforward. There are buttons
that should help you e.g. create a collaboration or delete a user. If
anything is unclear, please contact us via
`Discord <https://discord.com/invite/yAyFf6Y>`__.


.. figure:: /images/ui-screenshot.png

    Screenshot of the vantage6 UI

.. _use-python-client:

Python client
^^^^^^^^^^^^^

It is assumed you installed the :ref:`client install`. The Python client
aims to completely cover the vantage6-server communication
possibilities. It can create computation tasks and collect their
results, manage organizations, collaborations, users, etc. The server
hosts an API which the client uses for this purpose.

The methods in the library are all
documented in their docstring, you can view them using ``help(...)`` ,
e.g. ``help(client.user.create)`` will show you the parameters needed to
create a new user:

.. raw:: html

   <details>
   <summary><a>Example help function</a></summary>

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
   #    data_format : str, optional
   #        IO data format used, by default LEGACY
   #    database: str, optional
   #        Name of the database to use. This should match the key
   #        in the node configuration files. If not specified the
   #        default database will be tried.
   #
   #    Returns
   #    -------
   #    dict
   #        Containing the task information

.. raw:: html

   </details>

In :ref:`authentication` and sections after that, there are more examples on
how to use the Python client.

The following groups (related to the :ref:`concepts`) of methods are
available, most of them have a ``list()``, ``create()``, ``delete()``
and ``get()`` method attached.

-  ``client.user``
-  ``client.organization``
-  ``client.rule``
-  ``client.role``
-  ``client.collaboration``
-  ``client.task``
-  ``client.result``
-  ``client.util``
-  ``client.node``

.. _authentication:

Authentication
""""""""""""""

This section and the following sections introduce some minimal examples for
administrative tasks that you can perform with our
:ref:`use-python-client`. We start by authenticating.

To authenticate, we create a config file to store our login information.
We do this so we do not have to define the ``server_url``,
``server_port`` and so on every time we want to use the client.
Moreover, it enables us to separate the sensitive information (login
details, organization key) that you do not want to make publicly
available, from other parts of the code you might write later (e.g. on
submitting particular tasks) that you might want to share publicly.

.. code:: python

   # config.py

   server_url = "https://MY VANTAGE6 SERVER" # e.g. https://petronas.vantage6.ai or
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

   from vantage6.client import Client

   # Note: we assume here the config.py you just created is in the current directory.
   # If it is not, then you need to make sure it can be found on your PYTHONPATH
   import config

   # Initialize the client object, and run the authentication
   client = Client(config.server_url, config.server_port, config.server_api,
                   verbose=True)
   client.authenticate(config.username, config.password)

   # Optional: setup the encryption, if you have an organization_key
   client.setup_encryption(config.organization_key)

.. note::
    Above, we have added ``verbose=True`` as additional argument when creating
    the Client(…) object. This will print much more information that can be
    used to debug the issue.

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

   from vantage6.common import (warning, error, info, debug, bytes_to_base64s, check_config_write_permissions)
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
:ref:`concepts`). You will need to find
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
need it when you :ref:`node-configure` the node.

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
This container assumes a comma-separated (\*.csv) file as input, and will
compute the average over one of the named columns. We'll assume the
nodes in your collaboration have been configured to look at a
comma-separated database, i.e. their config contains something like

::

     databases:
         default: /path/to/my/example.csv
         my_other_database: /path/to/my/example2.csv

so that the third requirement is also met. As an end-user running the
algorithm, you'll need to align with the node owner about which database
name is used for the database you are interested in. For more details, see
how to :ref:`node-configure` your node.

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

**Creating a task that runs the master algorithm**

Now, we have two options: create a task that will run the master
algorithm (which runs on one node and may spawns subtasks on other nodes),
or create a task that will (only) run the RPC methods (which are run
on each node). Typically, the RPC methods only run the node local analysis
(e.g. compute the averages per node), whereas the master algorithms
performs aggregation of those results as well (e.g. starts the node
local analyses and then also computes the overall average). First, let
us create a task that runs the master algorithm of the
``harbor2.vantage6.ai/demo/average`` container

.. code:: python

   input_ = {'method': 'master',
             'kwargs': {'column_name': 'age'},
             'master': True}

   average_task = client.task.create(collaboration=1,
                                     organizations=[2,3],
                                     name="an-awesome-task",
                                     image="harbor2.vantage6.ai/demo/average",
                                     description='',
                                     input=input_,
                                     data_format='json')

Note that the ``kwargs`` we specified in the ``input_`` are specific to
this algorithm: this algorithm expects an argument ``column_name`` to be
defined, and will compute the average over the column with that name.
Furthermore, note that here we created a task for collaboration with id
``1`` (i.e. our ``example_collab1``) and the organizations with id ``2``
and ``3`` (i.e. ``example_org1`` and ``example_org2``). I.e. the
algorithm need not necessarily be run on *all* the organizations
involved in the collaboration. Finally, note that
``client.task.create()`` has an optional argument called ``database``.
Suppose that we would have wanted to run this analysis on the database
called ``my_other_database`` instead of the ``default`` database, we
could have specified an additional ``database = 'my_other_database'``
argument. Check ``help(client.task.create)`` for more information.

**Creating a task that runs the RPC algorithm**

You might be interested to know output of the RPC algorithm (in this
example: the averages for the 'age' column for each node). In that case,
you can run only the RPC algorithm, omitting the aggregation that the
master algorithm will normally do:

.. code:: python

   input_ = {'method': 'average_partial',
             'kwargs': {'column_name': 'age'},
             'master': False}

   average_task = client.task.create(collaboration=1,
                                     organizations=[2,3],
                                     name="an-awesome-task",
                                     image="harbor2.vantage6.ai/demo/average",
                                     description='',
                                     input=input_,
                                     data_format='json')

**Inspecting the results**

Of course, it will take a little while to run your algorithm. You can
use the following code snippet to run a loop that checks the server
every 3 seconds to see if the task has been completed:

.. code:: python

   print("Waiting for results")
   task_id = average_task['id']
   task_info = client.task.get(task_id)
   while not task_info.get("complete"):
       task_info = client.task.get(task_id, include_results=True)
       print("Waiting for results")
       time.sleep(3)

   print("Results are ready!")

When the results are in, you can get the result_id from the task object:

.. code:: python

   result_id = task_info['id']

and then retrieve the results

.. code:: python

   result_info = client.result.list(task=result_id)

The number of results may be different depending on what you run, but
for the master algorithm in this example, we can retrieve it using:

.. code:: python

   >>> result_info['data'][0]['result']
   {'average': 53.25}

while for the RPC algorithm, dispatched to two nodes, we can retrieve it
using

.. code:: python

   >>> result_info['data'][0]['result']
   {'sum': 253, 'count': 4}
   >>> result_info['data'][1]['result']
   {'sum': 173, 'count': 4}

.. _use-R-client:

R Client
^^^^^^^^

It is assumed you installed the :ref:`r client install`. The R client can
create tasks and retrieve their results. If you want to do more
administrative tasks, either use the API directly or use the
:ref:`use-python-client`.

Initialization of the R client can be done by:

.. code:: r

   setup.client <- function() {
     # Username/password should be provided by the administrator of
     # the server.
     username <- "username@example.com"
     password <- "password"

     host <- 'https://petronas.vantage6.ai:443'
     api_path <- ''

     # Create the client & authenticate
     client <- vtg::Client$new(host, api_path=api_path)
     client$authenticate(username, password)

     return(client)
   }

   # Create a client
   client <- setup.client()

Then this client can be used for the different algorithms. Refer to the
README in the repository on how to call the algorithm. Usually this
includes installing some additional client-side packages for the
specific algorithm you are using.

.. warning::
    The R client is subject to change. We aim to make it more similar to the
    Python client.

Example
"""""""

This example shows how to run the vantage6 implementation of a federated Cox
Proportional Hazard regression model. First you need to install the client side
of the algorithm by:

.. code:: r

   devtools::install_github('iknl/vtg.coxph', subdir="src")

This is the code to run the coxph:

.. code:: r

   print( client$getCollaborations() )

   # Should output something like this:
   #   id     name
   # 1  1 ZEPPELIN
   # 2  2 PIPELINE

   # Select a collaboration
   client$setCollaborationId(1)

   # Define explanatory variables, time column and censor column
   expl_vars <- c("Age","Race2","Race3","Mar2","Mar3","Mar4","Mar5","Mar9",
                  "Hist8520","hist8522","hist8480","hist8501","hist8201",
                  "hist8211","grade","ts","nne","npn","er2","er4")
   time_col <- "Time"
   censor_col <- "Censor"

   # vtg.coxph contains the function `dcoxph`.
   result <- vtg.coxph::dcoxph(client, expl_vars, time_col, censor_col)

.. _use-server-api:

Server API
^^^^^^^^^^

The server API is documented in the path ``https://SERVER[/api_path]/apidocs``.
For Petronas, the API docs can thus be found at
https://petronas.vantage6.ai/apidocs.

This page will show you which API
endpoints exist and how you can use them. All endpoints communicate via
HTTP requests, so you can communicate with them using any platform or
programming language that supports HTTP requests.

.. _use-node:

Node
----

Introduction
^^^^^^^^^^^^

It is assumed you have successfully installed `vantage6-node <./>`__. To
verify this you can run the command ``vnode --help``. If that prints a
list of commands, the installation is completed. Also, make sure that
Docker is running.

.. note::
    An organization runs a node for each of the collaborations it participates
    in

Quick start
"""""""""""

To create a new node, run the command below. A menu will be started that
allows you to set up a node configuration file. For more details, check
out the :ref:`node-configure` section.

::

   vnode new

To run a node, execute the command below. The ``--attach`` flag will
cause log output to be printed to the console.

::

   vnode start --name <your_node> --attach

Finally, a node can be stopped again with:

::

   vnode stop --name <your_node>

Available commands
""""""""""""""""""

Below is a list of all commands you can run for your node(s). To see all
available options per command use the ``--help`` flag,
i.e. ``vnode start --help`` .

+---------------------+------------------------------------------------+
| **Command**         | **Description**                                |
+=====================+================================================+
| ``vnode new``       | Create a new node configuration file           |
+---------------------+------------------------------------------------+
| ``vnode start``     | Start a node                                   |
+---------------------+------------------------------------------------+
| ``vnode stop``      | Stop one or all nodes                          |
+---------------------+------------------------------------------------+
| ``vnode files``     | List the files of a node                       |
+---------------------+------------------------------------------------+
| ``vnode attach``    | Print the node logs to the console             |
+---------------------+------------------------------------------------+
| ``vnode list``      | List all available nodes                       |
+---------------------+------------------------------------------------+
| ``vnode             | Create and upload a new public key for your    |
| create-private-key``| organization                                   |
+---------------------+------------------------------------------------+

See the following sections on how to configure and maintain a
vantage6-node instance:

-  :ref:`node-configure`
-  :ref:`node-security`
-  :ref:`node-logging`

.. _node-configure:

Configure
^^^^^^^^^

The vantage6-node requires a configuration file to run. This is a
``yaml`` file with a specific format. To create an initial configuration
file, start the configuration wizard via: ``vnode new`` . You can also
create and/or edit this file manually.

The directory where the configuration file is stored depends on your
operating system (OS). It is possible to store the configuration file at
**system** or at **user** level. By default, node configuration files
are stored at **user** level. The default directories per OS are as
follows:

+----------+-------------------------+--------------------------------+
| **Opera- | **System-folder**       | **User-folder**                |
| ting     |                         |                                |
| System** |                         |                                |
+==========+=========================+================================+
| Windows  | ``C:\ProgramData        | ``C:\Users\<user>              |
|          | \vantage\node``         | \AppData\Local\vantage\node``  |
+----------+-------------------------+--------------------------------+
| MacOS    | ``/Library/Application  | ``/Users/<user>/Library/Appli  |
|          | Support/vantage6/node`` | cation Support/vantage6/node`` |
+----------+-------------------------+--------------------------------+
| Linux    | ``/etc/vantage6/node``  | ``/home/<user>                 |
|          |                         | /.config/vantage6/node``       |
+----------+-------------------------+--------------------------------+

.. warning::
    The command ``vnode`` looks in certain directories by default. It is
    possible to use any directory and specify the location with the ``--config``
    flag. However, note that using a different directory requires you to
    specify the ``--config`` flag every time!

.. _node-configure-structure:

Configuration file structure
""""""""""""""""""""""""""""

Each node instance (configuration) can have multiple environments. You
can specify these under the key ``environments`` which allows four
types: ``dev`` , ``test``,\ ``acc`` and ``prod`` . If you do not want to
specify any environment, you should only specify the key ``application``
(not within ``environments``) .

.. raw:: html

   <details>
   <summary><a>Example configuration file</a></summary>

.. code:: yaml

   application:

     # API key used to authenticate at the server.
     api_key: ***

     # URL of the vantage6 server
     server_url: https://petronas.vantage6.ai

     # port the server listens to
     port: 443

     # API path prefix that the server uses. Usually '/api' or an empty string
     api_path: ''

     # subnet of the VPN server
     vpn_subnet: 10.76.0.0/16

     # add additional environment variables to the algorithm containers.
     # this could be usefull for passwords or other things that algorithms
     # need to know about the node it is running on
     # OPTIONAL
     algorithm_env:

       # in this example the environment variable 'player' has
       # the value 'Alice' inside the algorithm container
       player: Alice

     # specify custom Docker images to use for starting the different
     # components.
     # OPTIONAL
     images:
       node: harbor2.vantage6.ai/infrastructure/node:petronas
       alpine: harbor2.vantage6.ai/infrastructure/alpine
       vpn_client: harbor2.vantage6.ai/infrastructure/vpn_client
       network_config: harbor2.vantage6.ai/infrastructure/vpn_network

     # path or endpoint to the local data source. The client can request a
     # certain database to be used if it is specified here. They are
     # specified as label:local_path pairs.
     databases:
       default: D:\data\datafile.csv

     # end-to-end encryption settings
     encryption:

       # whenever encryption is enabled or not. This should be the same
       # as the `encrypted` setting of the collaboration to which this
       # node belongs.
       enabled: false

       # location to the private key file
       private_key: /path/to/private_key.pem

     # To control which algorithms are allowed at the node you can set
     # the allowed_images key. This is expected to be a valid regular
     # expression
     allowed_images:
       - ^harbor.vantage6.ai/[a-zA-Z]+/[a-zA-Z]+

     # credentials used to login to private Docker registries
     docker_registries:
       - registry: docker-registry.org
         username: docker-registry-user
         password: docker-registry-password

     # Settings for the logger
     logging:
         # Controls the logging output level. Could be one of the following
         # levels: CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET
         level:        DEBUG

         # Filename of the log-file, used by RotatingFileHandler
         file:         my_node.log

         # whenever the output needs to be shown in the console
         use_console:  True

         # The number of log files that are kept, used by RotatingFileHandler
         backup_count: 5

         # Size kb of a single log file, used by RotatingFileHandler
         max_size:     1024

         # format: input for logging.Formatter,
         format:       "%(asctime)s - %(name)-14s - %(levelname)-8s - %(message)s"
         datefmt:      "%Y-%m-%d %H:%M:%S"

     # directory where local task files (input/output) are stored
     task_dir: C:\Users\<your-user>\AppData\Local\vantage6\node\tno1

.. raw:: html

   </details>

.. note::
    We use `DTAP for key environments <https://en.wikipedia.org/wiki/Development,_testing,_acceptance_and_production>`__.
    In short:

    - ``dev``: Development environment. It is ok to break things here
    - ``test``: Testing environment. Here, you can verify that everything
      works as expected. This environment should resemble the target
      environment where the final solution will be deployed as much as
      possible.
    - ``acc``: Acceptance environment. If the tests were successful, you can
      try this environment, where the final user will test his/her analysis
      to verify if everything meets his/her expectations.
    - ``prod``: Production environment. The version of the proposed solution
      where the final analyses are executed.


Configure using the Wizard
""""""""""""""""""""""""""

The most straightforward way of creating a new server configuration is
using the command ``vnode new`` which allows you to configure the most
basic settings.

By default, the configuration is stored at user level, which makes this
configuration available only for your user. In case you want to use a
system directory you can add the ``--system`` flag when invoking the
``vnode new`` command.

Update configuration
""""""""""""""""""""

To update a configuration you need to modify the created ``yaml`` file.
To see where this file is located, you can use the command
``vnode files`` . Do not forget to specify the flag ``--system`` in case
of a system-wide configuration or the ``--user`` flag in case of a
user-level configuration.

Local test setup
""""""""""""""""

Check the section on :ref:`use-server-local` of the server if
you want to run both the node and server on the same machine.

.. _node-security:

Security
^^^^^^^^

As a data owner it is important that you take the necessary steps to
protect your data. Vantage6 allows algorithms to run on your data and
share the results with other parties. It is important that you review
the algorithms before allowing them to run on your data.

Once you approved the algorithm, it is important that you can verify
that the approved algorithm is the algorithm that runs on your data.
There are two important steps to be taken to accomplish this:

-  Set the (optional) ``allowed_images`` option in the
   node-configuration file. You can specify a regex expression here. For
   example

   1. ``^harbor2.vantage6.ai/[a-zA-Z]+/[a-zA-Z]+``: allows all images
      from the vantage6 registry
   2. ``^harbor2.vantage6.ai/algorithms/glm``: only allows this specific
      image, but all builds of this image
   3. ``^harbor2.vantage6.ai/algorithms/glm@sha256:82becede498899ec668628e7cb0a``
      ``d87b6e1c371cb8a1e597d83a47fac21d6af3``:
      allows only this specific build from the GLM to run on your data

-  Enable ``DOCKER_CONTENT_TRUST`` to verify the origin of the image.
   For more details see the `documentation from
   Docker <https://docs.docker.com/engine/security/trust/>`__.

.. warning::
    By enabling ``DOCKER_CONTENT_TRUST`` you might not be able to use
    certain algorithms. You can check this by verifying that the images you want
    to be used are signed.

    In case you are using our Docker repository you need to use
    harbor\ **2**.vantage6.ai as harbor.vantage6.ai does not have a notary.

.. _node-logging:

Logging
^^^^^^^

Logging is enabled by default. To configure the logger, look at the logging section
in the example configuration file in :ref:`node-configure-structure`.

.. todo update link above

Useful commands:

1. ``vnode files``: shows you where the log file is stored
2. ``vnode attach``: shows live logs of a running server in your current
   console. This can also be achieved when starting the node with
   ``vnode start --attach``

.. _use-server:

Server
------

Introduction
^^^^^^^^^^^^

It is assumed that you successfully installed the vantage6 :ref:`install-server`. To
verify this, you can run the command ``vserver --help`` . If that prints a list of
commands, your installation is successful. Also, make sure that Docker
is running.

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

The following sections explain how to use these commands to configure
and maintain a vantage6-server instance:

-  :ref:`server-configure`
-  :ref:`server-import`
-  :ref:`server-deployment`
-  :ref:`server-logging`
-  :ref:`server-shell`

.. _server-configure:

Configure
^^^^^^^^^

The vantage6-server requires a configuration file to run. This is a
``yaml`` file with specific contents. You can create and edit this file
manually. To create an initial configuration file you can also use the
configuration wizard: ``vserver new``.

The directory where to store the configuration file depends on you
operating system (OS). It is possible to store the configuration file at
**system** or at **user** level. By default, server configuration files
are stored at **system** level. The default directories per OS are as
follows:

+---------+----------------------------+------------------------------------+
| **OS**  | **System**                 | **User**                           |
+=========+============================+====================================+
| Windows | ``C:\ProgramData           | ``C:\Users\<user>                  |
|         | \vantage6\server``         | \AppData\Local\vantage6\server\``  |
+---------+----------------------------+------------------------------------+
| Macos   | ``/Library/Application     | ``/Users/<user>/Library/Appl       |
|         | Support/vantage6/server/`` | ication Support/vantage6/server/`` |
+---------+----------------------------+------------------------------------+
| Ubuntu  | ``/etc/xdg/vantage6/       | ``~/.config/vantage6/server/``     |
|         | server/``                  |                                    |
+---------+----------------------------+------------------------------------+

.. warning::
    The command ``vserver`` looks in certain directories by default. It is
    possible to use any directory and specify the location with the ``--config``
    flag. However, note that using a different directory requires you to specify
    the ``--config`` flag every time!

.. _server-config-file-structure:

Configuration file structure
""""""""""""""""""""""""""""

Each server instance (configuration) can have multiple environments. You
can specify these under the key ``environments`` which allows four
types: ``dev`` ,\ ``test``, ``acc`` and ``prod`` . If you do not want to
specify any environment, you should only specify the key ``application``
(not within ``environments``) .

.. raw:: html

   <details>
   <summary><a>Example configuration file</a></summary>

.. code:: yaml

   application:
     ...
   environments:
     test:

       # Human readable description of the server instance. This is to help
       # your peers to identify the server
       description: Test

       # Should be prod, acc, test or dev. In case the type is set to test
       # the JWT-tokens expiration is set to 1 day (default is 6 hours). The
       # other types can be used in future releases of vantage6
       type: test

       # IP adress to which the server binds. In case you specify 0.0.0.0
       # the server listens on all interfaces
       ip: 0.0.0.0

       # Port to which the server binds
       port: 5000

       # API path prefix. (i.e. https://yourdomain.org/api_path/<endpoint>). In the
       # case you use a referse proxy and use a subpath, make sure to include it
       # here also.
       api_path: /api

       # The URI to the server database. This should be a valid SQLAlchemy URI,
       # e.g. for an Sqlite database: sqlite:///database-name.sqlite,
       # or Postgres: postgresql://username:password@172.17.0.1/database).
       uri: sqlite:///test.sqlite

       # This should be set to false in production as this allows to completely
       # wipe the database in a single command. Useful to set to true when
       # testing/developing.
       allow_drop_all: True

       # The secret key used to generate JWT authorization tokens. This should
       # be kept secret as others are able to generate access tokens if they
       # know this secret. This parameter is optional. In case it is not
       # provided in the configuration it is generated each time the server
       # starts. Thereby invalidating all previous distributed keys.
       # OPTIONAL
       jwt_secret_key: super-secret-key! # recommended but optional

       # Settings for the logger
       logging:

         # Controls the logging output level. Could be one of the following
         # levels: CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET
         level:        DEBUG

         # Filename of the log-file, used by RotatingFileHandler
         file:         test.log

         # Whether the output is shown in the console or not
         use_console:  True

         # The number of log files that are kept, used by RotatingFileHandler
         backup_count: 5

         # Size in kB of a single log file, used by RotatingFileHandler
         max_size:     1024

         # format: input for logging.Formatter,
         format:       "%(asctime)s - %(name)-14s - %(levelname)-8s - %(message)s"
         datefmt:      "%Y-%m-%d %H:%M:%S"

       # Configure a smtp mail server for the server to use for administrative
       # purposes. e.g. allowing users to reset their password.
       # OPTIONAL
       smtp:
         port: 587
         server: smtp.yourmailserver.com
         username: your-username
         password: super-secret-password

       # Set an email address you want to direct your users to for support
       # (defaults to the address you set above in the SMTP server or otherwise
       # to support@vantage6.ai)
       support_email: your-support@email.com

       # set how long reset token provided via email are valid (default 1 hour)
       email_token_validity_minutes: 60

       # If algorithm containers need direct communication between each other
       # the server also requires a VPN server. (!) This must be a EduVPN
       # instance as vantage6 makes use of their API (!)
       # OPTIONAL
       vpn_server:
           # the URL of your VPN server
           url: https://your-vpn-server.ext

           # OATH2 settings, make sure these are the same as in the
           # configuration file of your EduVPN instance
           redirect_url: http://localhost
           client_id: your_VPN_client_user_name
           client_secret: your_VPN_client_user_password

           # Username and password to acccess the EduVPN portal
           portal_username: your_eduvpn_portal_user_name
           portal_userpass: your_eduvpn_portal_user_password

     prod:
       ...

.. raw:: html

   </details>


.. note::
    We use `DTAP for key environments <https://en.wikipedia.org/wiki/Development,_testing,_acceptance_and_production>`__.
    In short:

    - ``dev`` Development environment. It is ok to break things here
    - ``test`` Testing environment. Here, you can verify that everything
      works as expected. This environment should resemble the target
      environment where the final solution will be deployed as much as
      possible.
    - ``acc`` Acceptance environment. If the tests were successful, you can
      try this environment, where the final user will test his/her analysis
      to verify if everything meets his/her expectations.
    - ``prod`` Production environment. The version of the proposed solution
      where the final analyses are executed.


Configuration wizard
""""""""""""""""""""

The most straightforward way of creating a new server configuration is
using the command ``vserver new`` which allows you to configure most
settings. The :ref:`server-configure` section details
what each setting represents.

By default, the configuration is stored at system level, which makes
this configuration available for *all* users. In case you want to use a
user directory you can add the ``--user`` flag when invoking the
``vserver new`` command.

Update configuration
""""""""""""""""""""

To update a configuration you need to modify the created ``yaml`` file.
To see where this file is located you can use the command
``vserver files`` . Do not forget to specify the flag ``--system`` in
case of a system-wide configuration or the flag ``--user`` in case of a
user-level configuration.

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

:warning:
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

.. warning::
    All users that are imported using ``vserver import`` receive the superuser
    role. We are looking into ways to also be able to import roles. For more
    background info refer to this
    `issue <https://github.com/vantage6/vantage6/issues/71>`__.

You can easily create a set of test users, organizations and collaborations by
using a batch import. To do this, use the
``vserver import /path/to/file.yaml`` command. An example ``yaml`` file is
provided here:

.. raw:: html

   <details>
   <summary><a>Example batch import</a></summary>

.. code:: yaml

   organizations:

     - name:       IKNL
       domain:     iknl.nl
       address1:   Godebaldkwartier 419
       address2:
       zipcode:    3511DT
       country:    Netherlands
       users:
         - username: admin
           firstname: admin
           lastname: robot
           password: password
         - username: frank@iknl.nl
           firstname: Frank
           lastname: Martin
           password: password
         - username: melle@iknl.nl
           firstname: Melle
           lastname: Sieswerda
           password: password
       public_key: LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQ0lqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FnOEFNSUlDQ2dLQ0FnRUF2eU4wWVZhWWVZcHVWRVlpaDJjeQphTjdxQndCUnB5bVVibnRQNmw2Vk9OOGE1eGwxMmJPTlQyQ1hwSEVGUFhZQTFFZThQRFZwYnNQcVVKbUlseWpRCkgyN0NhZTlIL2lJbUNVNnViUXlnTzFsbG1KRTJQWDlTNXVxendVV3BXMmRxRGZFSHJLZTErUUlDRGtGSldmSEIKWkJkczRXMTBsMWlxK252dkZ4OWY3dk8xRWlLcVcvTGhQUS83Mm52YlZLMG9nRFNaUy9Jc1NnUlk5ZnJVU1FZUApFbGVZWUgwYmI5VUdlNUlYSHRMQjBkdVBjZUV4dXkzRFF5bXh2WTg3bTlkelJsN1NqaFBqWEszdUplSDAwSndjCk80TzJ0WDVod0lLL1hEQ3h4eCt4b3cxSDdqUWdXQ0FybHpodmdzUkdYUC9wQzEvL1hXaVZSbTJWZ3ZqaXNNaisKS2VTNWNaWWpkUkMvWkRNRW1QU29rS2Y4UnBZUk1lZk0xMWtETTVmaWZIQTlPcmY2UXEyTS9SMy90Mk92VDRlRgorUzVJeTd1QWk1N0ROUkFhejVWRHNZbFFxTU5QcUpKYlRtcGlYRWFpUHVLQitZVEdDSC90TXlrRG1JK1dpejNRCjh6SVo1bk1IUnhySFNqSWdWSFdwYnZlTnVaL1Q1aE95aE1uZHU0c3NpRkJyUXN5ZGc1RlVxR3lkdE1JMFJEVHcKSDVBc1ovaFlLeHdiUm1xTXhNcjFMaDFBaDB5SUlsZDZKREY5MkF1UlNTeDl0djNaVWRndEp5VVlYN29VZS9GKwpoUHVwVU4rdWVTUndGQjBiVTYwRXZQWTdVU2RIR1diVVIrRDRzTVQ4Wjk0UVl2S2ZCanU3ZXVKWSs0Mmd2Wm9jCitEWU9ZS05qNXFER2V5azErOE9aTXZNQ0F3RUFBUT09Ci0tLS0tRU5EIFBVQkxJQyBLRVktLS0tLQo=

     - name:       Small Organization
       domain:     small-organization.example
       address1:   Big Ambitions Drive 4
       address2:
       zipcode:    1234AB
       country:    Nowhereland
       users:
         - username: admin@small-organization.example
           firstname: admin
           lastname: robot
           password: password
         - username: stan
           firstname: Stan
           lastname: the man
           password: password
       public_key: LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQ0lqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FnOEFNSUlDQ2dLQ0FnRUF2eU4wWVZhWWVZcHVWRVlpaDJjeQphTjdxQndCUnB5bVVibnRQNmw2Vk9OOGE1eGwxMmJPTlQyQ1hwSEVGUFhZQTFFZThQRFZwYnNQcVVKbUlseWpRCkgyN0NhZTlIL2lJbUNVNnViUXlnTzFsbG1KRTJQWDlTNXVxendVV3BXMmRxRGZFSHJLZTErUUlDRGtGSldmSEIKWkJkczRXMTBsMWlxK252dkZ4OWY3dk8xRWlLcVcvTGhQUS83Mm52YlZLMG9nRFNaUy9Jc1NnUlk5ZnJVU1FZUApFbGVZWUgwYmI5VUdlNUlYSHRMQjBkdVBjZUV4dXkzRFF5bXh2WTg3bTlkelJsN1NqaFBqWEszdUplSDAwSndjCk80TzJ0WDVod0lLL1hEQ3h4eCt4b3cxSDdqUWdXQ0FybHpodmdzUkdYUC9wQzEvL1hXaVZSbTJWZ3ZqaXNNaisKS2VTNWNaWWpkUkMvWkRNRW1QU29rS2Y4UnBZUk1lZk0xMWtETTVmaWZIQTlPcmY2UXEyTS9SMy90Mk92VDRlRgorUzVJeTd1QWk1N0ROUkFhejVWRHNZbFFxTU5QcUpKYlRtcGlYRWFpUHVLQitZVEdDSC90TXlrRG1JK1dpejNRCjh6SVo1bk1IUnhySFNqSWdWSFdwYnZlTnVaL1Q1aE95aE1uZHU0c3NpRkJyUXN5ZGc1RlVxR3lkdE1JMFJEVHcKSDVBc1ovaFlLeHdiUm1xTXhNcjFMaDFBaDB5SUlsZDZKREY5MkF1UlNTeDl0djNaVWRndEp5VVlYN29VZS9GKwpoUHVwVU4rdWVTUndGQjBiVTYwRXZQWTdVU2RIR1diVVIrRDRzTVQ4Wjk0UVl2S2ZCanU3ZXVKWSs0Mmd2Wm9jCitEWU9ZS05qNXFER2V5azErOE9aTXZNQ0F3RUFBUT09Ci0tLS0tRU5EIFBVQkxJQyBLRVktLS0tLQo=

     - name:       Big Organization
       domain:     big-organization.example
       address1:   Offshore Accounting Drive 19
       address2:
       zipcode:    54331
       country:    Nowhereland
       users:
         - username: admin@big-organization.example
           firstname: admin
           lastname: robot
           password: password
       public_key: LS0tLS1CRUdJTiBQVUJMSUMgS0VZLS0tLS0KTUlJQ0lqQU5CZ2txaGtpRzl3MEJBUUVGQUFPQ0FnOEFNSUlDQ2dLQ0FnRUF2eU4wWVZhWWVZcHVWRVlpaDJjeQphTjdxQndCUnB5bVVibnRQNmw2Vk9OOGE1eGwxMmJPTlQyQ1hwSEVGUFhZQTFFZThQRFZwYnNQcVVKbUlseWpRCkgyN0NhZTlIL2lJbUNVNnViUXlnTzFsbG1KRTJQWDlTNXVxendVV3BXMmRxRGZFSHJLZTErUUlDRGtGSldmSEIKWkJkczRXMTBsMWlxK252dkZ4OWY3dk8xRWlLcVcvTGhQUS83Mm52YlZLMG9nRFNaUy9Jc1NnUlk5ZnJVU1FZUApFbGVZWUgwYmI5VUdlNUlYSHRMQjBkdVBjZUV4dXkzRFF5bXh2WTg3bTlkelJsN1NqaFBqWEszdUplSDAwSndjCk80TzJ0WDVod0lLL1hEQ3h4eCt4b3cxSDdqUWdXQ0FybHpodmdzUkdYUC9wQzEvL1hXaVZSbTJWZ3ZqaXNNaisKS2VTNWNaWWpkUkMvWkRNRW1QU29rS2Y4UnBZUk1lZk0xMWtETTVmaWZIQTlPcmY2UXEyTS9SMy90Mk92VDRlRgorUzVJeTd1QWk1N0ROUkFhejVWRHNZbFFxTU5QcUpKYlRtcGlYRWFpUHVLQitZVEdDSC90TXlrRG1JK1dpejNRCjh6SVo1bk1IUnhySFNqSWdWSFdwYnZlTnVaL1Q1aE95aE1uZHU0c3NpRkJyUXN5ZGc1RlVxR3lkdE1JMFJEVHcKSDVBc1ovaFlLeHdiUm1xTXhNcjFMaDFBaDB5SUlsZDZKREY5MkF1UlNTeDl0djNaVWRndEp5VVlYN29VZS9GKwpoUHVwVU4rdWVTUndGQjBiVTYwRXZQWTdVU2RIR1diVVIrRDRzTVQ4Wjk0UVl2S2ZCanU3ZXVKWSs0Mmd2Wm9jCitEWU9ZS05qNXFER2V5azErOE9aTXZNQ0F3RUFBUT09Ci0tLS0tRU5EIFBVQkxJQyBLRVktLS0tLQo=

   collaborations:

     - name: ZEPPELIN
       participants:
         - name: IKNL
           api_key: 123e4567-e89b-12d3-a456-426614174001
         - name: Small Organization
           api_key: 123e4567-e89b-12d3-a456-426614174002
         - name: Big Organization
           api_key: 123e4567-e89b-12d3-a456-426614174003
       tasks: ["hello-world"]
       encrypted: false

     - name: PIPELINE
       participants:
         - name: IKNL
           api_key: 123e4567-e89b-12d3-a456-426614174004
         - name: Big Organization
           api_key: 123e4567-e89b-12d3-a456-426614174005
       tasks: ["hello-world"]
       encrypted: false

     - name: SLIPPERS
       participants:
         - name: Small Organization
           api_key: 123e4567-e89b-12d3-a456-426614174006
         - name: Big Organization
           api_key: 123e4567-e89b-12d3-a456-426614174007
       tasks: ["hello-world", "hello-world"]
       encrypted: false

.. raw:: html

   </details>


.. _server-logging:

Logging
^^^^^^^

Logging is enabled by default. To configure the logger, look at the ``logging``
section in the example configuration in :ref:`server-config-file-structure`.

Useful commands:

1. ``vserver files``: shows you where the log file is stored
2. ``vserver attach``: show live logs of a running server in your
   current console. This can also be achieved when starting the server
   with ``vserver start --attach``

.. _server-shell:

Shell
^^^^^

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
"""""""""""""

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
"""""""""""""""

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
"""""

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
""""""""""""""

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
"""""

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
"""""""""""""""""

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

