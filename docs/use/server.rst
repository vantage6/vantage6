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

   # get the algorithm runs of all these tasks (which include the results)
   runs = organization.runs

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

Tasks, Runs and results
"""""""""""""""""

.. warning::
    Tasks (and runs) created from the shell are not picked up by nodes that are
    already running. The signal to notify them of a new task cannot be emitted
    this way. We therefore recommend sending tasks via the Python client.

A task is intended for one or more organizations. For each organization
the task is intended for, a corresponding algorithm run
should be created. Each task can have multiple runs, for example a
run from each organization. Each of these runs then contains the partial result
for that organization.

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
       initiator=iknl,
   )
   task.save()

   # input the algorithm container (docker-registry.org/image-name)
   # expects
   input_ = {
   }

   import datetime

   # now create a run model for each organization within the
   # collaboration. This could also be a subset
   for org in collaboration.organizations:
       run = db.Run(
           input=input_,
           organization=org,
           task=task,
           assigned_at=datetime.datetime.now()
       )
       run.save()

Tasks can have a child/parent relationship. Note that the ``job_id`` is the same
for parent and child tasks.

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
       initiator=iknl,
       parent=parent_task
   )
   child_task.save()

.. note::
    Tasks that share a ``job_id`` have access to the same temporary folder at
    the node. This allows for multi-stage algorithms.

Obtaining algorithm run data:

.. code:: python

   # obtain all Runs
   db.Run.get()

   # obtain only completed runs
   [run for run in db.Run.get() if run.complete]

   # obtain run by its unique id
   db.Run.get(1)

