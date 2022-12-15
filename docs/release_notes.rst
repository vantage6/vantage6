Release notes
=============

3.5.2
-----

*30 november 2022*

-  **Bugfix**

  -  Fix for automatic addition of column. This failed in some SQL
     dialects because reserved keywords (i.e. 'user' for PostgresQL) were
     not escaped
     (`PR#415 <https://github.com/vantage6/vantage6/pull/415>`__)
  -  Correct installation order for uWSGI in node and server docker file
     (`PR#414 <https://github.com/vantage6/vantage6/pull/414>`__)

.. _section-1:

3.5.1
-----

*30 november 2022*

-  **Bugfix**

 -  Backwards compatibility for which organization initiated a task
    between v3.0-3.4 and v3.5
    (`PR#412 <https://github.com/vantage6/vantage6/pull/413>`__)
 -  Fixed VPN client container. Entry script was not executable in Github
    pipelines
    (`PR#413 <https://github.com/vantage6/vantage6/pull/413>`__)

3.5.0
-----

*30 november 2022*

.. warning::
   When upgrading to 3.5.0, you might need to add the **otp_secret** column to
   the **user** table manually in the database. This may be avoided by upgrading
   to 3.5.2.

-  **Feature**

  -  Multi-factor authentication via TOTP has been added. Admins can enforce
     that all users enable MFA
     (`PR#376 <https://github.com/vantage6/vantage6/pull/376>`__,
     `Issue#355 <https://github.com/vantage6/vantage6/issues/355>`__).
  -  You can now request all tasks assigned by a given user
     (`PR#326 <https://github.com/vantage6/vantage6/pull/326>`__,
     `Issue#43 <https://github.com/vantage6/vantage6/issues/43>`__).
  -  The server support email is now settable in the configuration
     file, used to be fixed at ``support@vantage6.ai``
     (`PR#330 <https://github.com/vantage6/vantage6/pull/330>`__,
     `Issue#319 <https://github.com/vantage6/vantage6/issues/319>`__).
  -  When pickles are used, more task info is shown in the node logs
     (`PR#366 <https://github.com/vantage6/vantage6/pull/366>`__,
     `Issue#171 <https://github.com/vantage6/vantage6/issues/171>`__).

-  **Change**

  -  The ``harbor2.vantag6.ai/infrastructure/algorithm-base:[TAG]`` is
     tagged with the vantage6-client version that is already in the
     image (`PR#389 <https://github.com/vantage6/vantage6/pull/389>`__,
     `Issue#233 <https://github.com/vantage6/vantage6/issues/233>`__).
  -  The infrastructure base image has been updated to improve build
     time (`PR#406 <https://github.com/vantage6/vantage6/pull/406>`__,
     `Issue#250 <https://github.com/vantage6/vantage6/issues/250>`__).


3.4.2
-----

*3 november 2022*

-  **Bugfix**

  -  Fixed a bug in the local proxy server which made algorithm containers crash
     in case the `client.create_new_task` method was used
     (`PR#382 <https://github.com/vantage6/vantage6/pull/382>`_).
  -  Fixed a bug where the node crashed when a non existing image was sent in a
     task (`PR#375 <https://github.com/vantage6/vantage6/pull/375>`_).


3.4.0 & 3.4.1
-------------

*25 oktober 2022*

-  **Feature**

  -  Add columns to the SQL database on startup
     (`PR#365 <https://github.com/vantage6/vantage6/pull/365>`__,
     `ISSUE#364 <https://github.com/vantage6/vantage6/issues/364>`__).
     This simpifies the upgrading proces when a new column is added in
     the new release, as you do no longer need to manually add columns.
     When downgrading the columns will **not** be deleted.
  -  Docker wrapper for Parquet files
     (`PR#361 <https://github.com/vantage6/vantage6/pull/361>`__,
     `ISSUE#337 <https://github.com/vantage6/vantage6/issues/337>`__).
     Parquet provides a way to store tabular data with the datatypes
     included which is an advantage over CSV.
  -  When the node starts, or when the client is verbose initialized a
     banner to cite the vantage6 project is added
     (`PR#359 <https://github.com/vantage6/vantage6/pull/359>`__,
     `ISSUE#356 <https://github.com/vantage6/vantage6/issues/356>`__).
  -  In the client a waiting for results method is added
     (`PR#325 <https://github.com/vantage6/vantage6/pull/325>`__,
     `ISSUE#8 <https://github.com/vantage6/vantage6/issues/8>`__).
     Which allows you to automatically poll for results by using
     ``client.wait_for_results(...)``, for more info see
     ``help(client.wait_for_results)``.
  -  Added Github releases
     (`PR#358 <https://github.com/vantage6/vantage6/pull/358>`__,
     `ISSUE#357 <https://github.com/vantage6/vantage6/issues/357>`__).
  -  Added option to filter GET ``/role`` by user id in the Python client
     (`PR#328 <https://github.com/vantage6/vantage6/pull/328>`__,
     `ISSUE#213 <https://github.com/vantage6/vantage6/issues/213>`__).
     E.g.: ``client.role.list(user=...).``
  - In release process, build and release images for both ARM and x86
    architecture.

-  **Change**

  -  Unused code removed from the Makefile
     (`PR#324 <https://github.com/vantage6/vantage6/issues/357>`__,
     `ISSUE#284 <https://github.com/vantage6/vantage6/issues/284>`__).
  -  Pandas version is frozen to version 1.3.5
     (`PR#363 <https://github.com/vantage6/vantage6/pull/363>`__ ,
     `ISSUE#266 <https://github.com/vantage6/vantage6/issues/266>`__).

-  **Bugfix**

  -  Improve checks for non-existing resources in unittests
     (`PR#320 <https://github.com/vantage6/vantage6/pull/320>`__,
     `ISSUE#265 <https://github.com/vantage6/vantage6/issues/265>`__).
     Flask did not support negative ints, so the tests passed due to
     another 404 response.
  -  ``client.node.list`` does no longer filter by offline nodes
     (`PR#321 <https://github.com/vantage6/vantage6/pull/321>`__,
     `ISSUE#279 <https://github.com/vantage6/vantage6/issues/279>`__).

.. note::
   3.4.1 is a rebuild from 3.4.0 in which the all dependencies are fixed, as
   the build led to a broken server image.

3.3.7
-----

-  **Bugfix**

  -  The function ``client.util.change_my_password()`` was updated
     (`Issue #333 <https://github.com/vantage6/vantage6/issues/333>`__)

3.3.6
-----

-  **Bugfix**

  -  Temporary fix for a bug that prevents the master container from
     creating tasks in an encrypted collaboration. This temporary fix
     disables the parallel encryption module in the local proxy. This
     functionality will be restored in a future release.

.. note::
    This version is also the first version where the User Interface is available
    in the right version. From this point onwards, the user interface changes
    will also be part of the release notes.

3.3.5
-----

-  **Feature**

  -  The release pipeline has been expanded to automatically push new
     Docker images of node/server to the harbor2 service.

-  **Bugfix**

  -  The VPN IP address for a node was not saved by the server using
     the PATCH ``/node`` endpoint, while this functionality is required
     to use the VPN

.. note::
    Note that 3.3.4 was only released on PyPi and that version is identical
    to 3.3.5. That version was otherwise skipped due to a temporary mistake
    in the release pipeline.

3.3.3
-----

-  **Bugfix**

  -  Token refresh was broken for both users and nodes.
     (`Issue#306 <https://github.com/vantage6/vantage6/issues/306>`__,
     `PR#307 <https://github.com/vantage6/vantage6/pull/307>`__)
  -  Local proxy encrpytion was broken. This prefented algorithms from
     creating sub tasks when encryption was enabled.
     (`Issue#305 <https://github.com/vantage6/vantage6/issues/305>`__,
     `PR#308 <https://github.com/vantage6/vantage6/pull/308>`__)

3.3.2
-----

-  **Bugfix**

  -  ``vpn_client_image`` and ``network_config_image`` are settable
     through the node configuration file.
     (`PR#301 <https://github.com/vantage6/vantage6/pull/301>`__,
     `Issue#294 <https://github.com/vantage6/vantage6/issues/294>`__)
  -  The option ``--all`` from ``vnode stop`` did not stop the node
     gracefully. This has been fixed. It is possible to force the nodes
     to quit by using the ``--force`` flag.
     (`PR#300 <https://github.com/vantage6/vantage6/pull/300>`__,
     `Issue#298 <https://github.com/vantage6/vantage6/issues/298>`__)
  -  Nodes using a slow internet connection (high ping) had issues with
     connecting to the websocket channel.
     (`PR#299 <https://github.com/vantage6/vantage6/pull/299>`__,
     `Issue#297 <https://github.com/vantage6/vantage6/issues/297>`__)

3.3.1
-----

-  **Bugfix**

  -  Fixed faulty error status codes from the ``/collaboration``
     endpoint
     (`PR#287 <https://github.com/vantage6/vantage6/pull/287>`__).
  -  *Default* roles are always returned from the ``/role`` endpoint.
     This fixes the error when a user was assigned a *default* role but
     could not reach anything (as it could not view its own role)
     (`PR#286 <https://github.com/vantage6/vantage6/pull/286>`__).
  -  Performance upgrade in the ``/organization`` endpoint. This caused
     long delays when retrieving organization information when the
     organization has many tasks
     (`PR#288 <https://github.com/vantage6/vantage6/pull/288>`__).
  -  Organization admins are no longer allowed to create and delete
     nodes as these should be managed at collaboration level.
     Therefore, the collaboration admin rules have been extended to
     include create and delete nodes rules
     (`PR#289 <https://github.com/vantage6/vantage6/pull/289>`__).
  -  Fixed some issues that made ``3.3.0`` incompatible with ``3.3.1``
     (`Issue#285 <https://github.com/vantage6/vantage6/issues/285>`__).

3.3.0
-----

-  **Feature**

  -  Login requirements have been updated. Passwords are now required
     to have sufficient complexity (8+ characters, and at least 1
     uppercase, 1 lowercase, 1 digit, 1 special character). Also, after
     5 failed login attempts, a user account is blocked for 15 minutes
     (these defaults can be changed in a server config file).
  -  Added endpoint ``/password/change`` to allow users to change their
     password using their current password as authentication. It is no
     longer possible to change passwords via ``client.user.update()``
     or via a PATCH ``/user/{id}`` request.
  -  Added the default roles ‘viewer’, ‘researcher’, ‘organization
     admin’ and ‘collaboration admin’ to newly created servers. These
     roles may be assigned to users of any organization, and should
     help users with proper permission assignment.
  -  Added option to filter get all roles for a specific user id in the
     GET ``/role`` endpoint.
  -  RabbitMQ has support for multiple servers when using
     ``vserver start``. It already had support for multiple servers
     when deploying via a Docker compose file.
  -  When exiting server logs or node logs with Ctrl+C, there is now an
     additional message alerting the user that the server/node is still
     running in the background and how they may stop them.

-  **Change**

  -  Node proxy server has been updated
  -  Updated PyJWT and related dependencies for improved JWT security.
  -  When nodes are trying to use a wrong API key to authenticate, they
     now receive a clear message in the node logs and the node exits
     immediately.
  -  When using ``vserver import``, API keys must now be provided for
     the nodes you create.
  -  Moved all swagger API docs from YAML files into the code. Also,
     corrected errors in them.
  -  API keys are created with UUID4 instead of UUID1. This prevents
     that UUIDs created milliseconds apart are not too similar.
  -  Rules for users to edit tasks were never used and have therefore
     been deleted.

-  **Bugfix**

  -  In the Python client, ``client.organization.list()`` now shows
     pagination metadata by default, which is consistent all other
     ``list()`` statements.
  -  When not providing an API key in ``vnode new``, there used to be
     an unclear error message. Now, we allow specifying an API key
     later and provide a clearer error message for any other keys with
     inadequate values.
  -  It is now possible to provide a name when creating a name, both
     via the Python client as via the server.
  -  A GET ``/role`` request crashed if parameter ``organization_id``
     was defined but not ``include_root``. This has been resolved.
  -  Users received an ‘unexpected error’ when performing a GET
     ``/collaboration?organization_id=<id>`` request and they didn’t
     have global collaboration view permission. This was fixed.
  -  GET ``/role/<id>`` didn’t give an error if a role didn’t exist.
     Now it does.

3.2.0
-----

-  **Feature**

  -  Horizontal scaling for the vantage6-server instance by adding
     support for RabbitMQ.
  -  It is now possible to connect other docker containers to the
     private algorithm network. This enables you to attach services to
     the algorithm network using the ``docker_services`` setting.
  -  Many additional select and filter options on API endpoints, see
     swagger docs endpoint (``/apidocs``). The new options have also
     been added to the Python client.
  -  Users are now always able to view their own data
  -  Usernames can be changed though the API

-  **Bugfix**

  -  (Confusing) SQL errors are no longer returned from the API.
  -  Clearer error message when an organization has multiple nodes for
     a single collaboration.
  -  Node no longer tries to connect to the VPN if it has no
     ``vpn_subnet`` setting in its configuration file.
  -  Fix the VPN configuration file renewal
  -  Superusers are no longer able to post tasks to collaborations its
     organization does not participate in. Note that superusers were
     never able to view the results of such tasks.
  -  It is no longer possible to post tasks to organization which do
     not have a registered node attach to the collaboration.
  -  The ``vnode create-private-key`` command no longer crashes if the
     ssh directory does not exist.
  -  The client no longer logs the password
  -  The version of the ``alpine`` docker image (that is used to set up
     algorithm runs with VPN) was fixed. This prevents that many
     versions of this image are downloaded by the node.
  -  Improved reading of username and password from docker registry,
     which can be capitalized differently depending on the docker
     version.
  -  Fix error with multiple-database feature, where default is now
     used if specific database is not found

3.1.0
-----

-  **Feature**

  -  Algorithm-to-algorithm communication can now take place over
     multiple ports, which the algorithm developer can specify in the
     Dockerfile. Labels can be assigned to each port, facilitating
     communication over multiple channels.
  -  Multi-database support for nodes. It is now also possible to
     assign multiple data sources to a single node in Petronas; this
     was already available in Harukas 2.2.0. The user can request a
     specific data source by supplying the *database* argument when
     creating a task.
  -  The CLI commands ``vserver new`` and ``vnode new`` have been
     extended to facilitate configuration of the VPN server.
  -  Filter options for the client have been extended.
  -  Roles can no longer be used across organizations (except for roles
     in the default organization)
  -  Added ``vnode remove`` command to uninstall a node. The command
     removes the resources attached to a node installation
     (configuration files, log files, docker volumes etc).
  -  Added option to specify configuration file path when running
     ``vnode create-private-key``.

-  **Bugfix**

  -  Fixed swagger docs
  -  Improved error message if docker is not running when a node is
     started
  -  Improved error message for ``vserver version`` and
     ``vnode version`` if no servers or nodes are running
  -  Patching user failed if users had zero roles - this has been
     fixed.
  -  Creating roles was not possible for a user who had permission to
     create roles only for their own organization - this has been
     corrected.

3.0.0
-----

-  **Feature**

  -  Direct algorithm-to-algorithm communication has been added. Via a
     VPN connection, algorithms can exchange information with one
     another.
  -  Pagination is added. Metadata is provided in the headers by
     default. It is also possible to include them in the output body by
     supplying an additional parameter\ ``include=metadata``.
     Parameters ``page`` and ``per_page`` can be used to paginate. The
     following endpoints are enabled:

     -  GET ``/result``
     -  GET ``/collaboration``
     -  GET ``/collaboration/{id}/organization``
     -  GET ``/collaboration/{id}/node``
     -  GET ``/collaboration/{id}/task``
     -  GET ``/organization``
     -  GET ``/role``
     -  GET ``/role/{id}/rule``
     -  GET ``/rule``
     -  GET ``/task``
     -  GET ``/task/{id}/result``
     -  GET ``/node``

  -  API keys are encrypted in the database
  -  Users cannot shrink their own permissions by accident
  -  Give node permission to update public key
  -  Dependency updates

-  **Bugfix**

  -  Fixed database connection issues
  -  Don’t allow users to be assigned to non-existing organizations by
     root
  -  Fix node status when node is stopped and immediately started up
  -  Check if node names are allowed docker names


2.3.0 - 2.3.4
-------------

-  **Feature**

  -  Allows for horizontal scaling of the server instance by adding
     support for RabbitMQ. Note that this has not been released for
     version 3(!)

-  **Bugfix**

  -  Performance improvements on the ``/organization`` endpoint

2.2.0
-----

-  **Feature**

  -  Multi-database support for nodes. It is now possible to assign
     multiple data sources to a single node. The user can request a
     specific data source by supplying the *database* argument when
     creating a task.
  -  The mailserver now supports TLS and SSL options

-  **Bugfix**

  -  Nodes are now disconnected more gracefully. This fixes the issue
     that nodes appear offline while they are in fact online
  -  Fixed a bug that prevented deleting a node from the collaboration
  -  A role is now allowed to have zero rules
  -  Some http error messages have improved
  -  Organization fields can now be set to an empty string

2.1.2 & 2.1.3
-------------

-  **Bugfix**

  -  Changes to the way the application interacts with the database.
     Solves the issue of unexpected disconnects from the DB and thereby
     freezing the application.

2.1.1
-----

-  **Bugfix**

  -  Updating the country field in an organization works again\\
  -  The ``client.result.list(...)`` broke when it was not able to
     deserialize one of the in- or outputs.

2.1.0
-----

-  **Feature**

  -  Custom algorithm environment variables can be set using the
     ``algorithm_env`` key in the configuration file. `See this Github
     issue <https://github.com/IKNL/vantage6-node/issues/32>`__.
  -  Support for non-file-based databases on the node. `See this Github
     issue <https://github.com/IKNL/vantage6/issues/66>`__.
  -  Added flag ``--attach`` to the ``vserver start`` and
     ``vnode start`` command. This directly attaches the log to the
     console.
  -  Auto updating the node and server instance is now limited to the
     major version. `See this Github
     issue <https://github.com/IKNL/vantage6/issues/65>`__.

     -  e.g. if you’ve installed the Trolltunga version of the CLI you
        will always get the Trolltunga version of the node and server.
     -  Infrastructure images are now tagged using their version major.
        (e.g. ``trolltunga`` or ``harukas`` )
     -  It is still possible to use intermediate versions by specifying
        the ``--image`` option when starting the node or server.
        (e.g. ``vserver start --image harbor.vantage6.ai/infrastructure/server:2.0.0.post1``
        )

-  **Bugfix**

  -  Fixed issue where node crashed if the database did not exist on
     startup. `See this Github
     issue <https://github.com/IKNL/vantage6/issues/67>`__.

2.0.0.post1
-----------

-  **Bugfix**

  -  Fixed a bug that prevented the usage of secured registry
     algorithms

2.0.0
-----

-  **Feature**

  -  Role/rule based access control

     -  Roles consist of a bundle of rules. Rules profided access to
        certain API endpoints at the server.
     -  By default 3 roles are created: 1) Container, 2) Node, 3) Root.
        The root role is assigned to the root user on the first run.
        The root user can assign rules and roles from there.
  -  Major update on the *python*-client. The client also contains
     management tools for the server (i.e. to creating users,
     organizations and managing permissions. The client can be imported
     from ``from vantage6.client import Client`` .
  -  You can use the agrument ``verbose`` on the client to output
     status messages. This is usefull for example when working with
     Jupyter notebooks.
  -  Added CLI ``vserver version`` , ``vnode version`` ,
     ``vserver-local version`` and ``vnode-local version`` commands to
     report the version of the node or server they are running
  -  The logging contains more information about the current setup, and
     refers to this documentation and our Discourd channel

-   **Bugfix**

  -  Issue with the DB connection. Session management is updated. Error
     still occurs from time to time but can be reset by using the
     endpoint ``/health/fix`` . This will be patched in a newer
     version.

1.2.3
-----

-  **Feature**

  -  The node is now compatible with the Harbor v2.0 API


1.2.2
-----

-  **Bug fixes**

  -  Fixed a bug that ignored the ``--system`` flag from
     ``vnode start``
  -  Logging output muted when the ``--config`` option is used in
     ``vnode start``
  -  Fixed config folder mounting point when the option ``--config``
     option is used in ``vnode start``

1.2.1
-----

-  **Bug fixes**

  -  starting the server for the first time resulted in a crash as the
     root user was not supplied with an email address.
  -  Algorithm containers could still access the internet through their
     host. This has been patched.

1.2.0
-----

-  **Features**

  -  Cross language serialization. Enabling algorithm developers to
     write algorithms that are not language dependent.
  -  Reset password is added to the API. For this purpose two endpoints
     have been added: ``/recover/lost``\ and ``recover/reset`` . The
     server config file needs to extended to be connected to a
     mail-server in order to make this work.
  -  User table in the database is extended to contain an email address
     which is mandatory.

-  **Bug fixes**

  -  Collaboration name needs to be unique
  -  API consistency and bug fixes:

     -  GET ``organization`` was missing domain key
     -  PATCH ``/organization`` could not patch domain
     -  GET ``/collaboration/{id}/node`` has been made consistent with
        ``/node``
     -  GET ``/collaboration/{id}/organization`` has been made
        consistent with ``/organization``
     -  PATCH ``/user`` root-user was not able to update users
     -  DELETE ``/user`` root-user was not able to delete users
     -  GET ``/task`` null values are now consistent: ``[]`` is
        replaced by ``null``
     -  POST, PATCH, DELETE ``/node`` root-user was not able to perform
        these actions
     -  GET ``/node/{id}/task`` output is made consistent with the

-  **other**

  -  ``questionairy`` dependency is updated to 1.5.2
  -  ``vantage6-toolkit`` repository has been merged with the
     ``vantage6-client`` as they were very tight coupled.

1.1.0
-----

-  **Features**

  -  new command ``vnode clean`` to clean up temporary docker volumes
     that are no longer used
  -  Version of the individual packages are printed in the console on
     startup
  -  Custom task and log directories can be set in the configuration
     file
  -  Improved **CLI** messages
  -  Docker images are only pulled if the remote version is newer. This
     applies both to the node/server image and the algorithm images
  -  Client class names have been simplified (``UserClientProtocol`` ->
     ``Client``)

-  **Bug fixes**

  -  Removed defective websocket watchdog. There still might be
     disconnection issues from time to time.

1.0.0
-----

-  **Updated Command Line Interface (CLI)**

  -  The commands ``vnode list`` , ``vnode start`` and the new
     command\ ``vnode attach`` are aimed to work with multiple nodes at
     a single machine.
  -  System and user-directories can be used to store configurations by
     using the ``--user/--system`` options. The node stores them by
     default at user level, and the server at system level.
  -  Current status (online/offline) of the nodes can be seen using
     ``vnode list`` , which also reports which environments are
     available per configuration.
  -  Developer container has been added which can inject the container
     with the source. ``vnode start --develop [source]``. Note that
     this Docker image needs to be build in advance from the
     ``development.Dockerfile`` and tag ``devcon``.
  -  ``vnode config_file`` has been replaced by ``vnode files`` which
     not only outputs the config file location but also the database
     and log file location.

-  **New database model**

  -  Improved relations between models, and with that, an update of the Python
     API.
  -  Input for the tasks is now stored in the result table. This was
     required as the input is encrypted individually for each
     organization (end-to-end encryption (E2EE) between organizations).
  -  The ``Organization`` model has been extended with the
     ``public_key`` (String) field. This field contains the public key
     from each organization, which is used by the E2EE module.
  -  The ``Collaboration`` model has been extended with the
     ``encrypted`` (Boolean) field which keeps track if all messages
     (tasks, results) need to be E2EE for this specific collaboration.
  -  The ``Task`` keeps track of the initiator (organization) of the
     organization. This is required to encrypt the results for the
     initiator.

-  **End to end encryption**

  -  All messages between all organizations are by default be
     encrypted.
  -  Each node requires the private key of the organization as it needs
     to be able to decrypt incoming messages. The private key should be
     specified in the configuration file using the ``private_key``
     label.
  -  In case no private key is specified, the node generates a new key
     an uploads the public key to the server.
  -  If a node starts (using ``vnode start``), it always checks if the
     ``public_key`` on the server matches the private key the node is
     currently using.
  -  In case your organization has multiple nodes running they should
     all point to the same private key.
  -  Users have to encrypt the input and decrypt the output, which can
     be simplified by using our client ``vantage6.client.Client`` \_\_
     for Python \_\_ or ``vtg::Client`` \_\_ for R.
  -  Algorithms are not concerned about encryption as this is handled
     at node level.

-  **Algorithm container isolation**

  -  Containers have no longer an internet connection, but are
     connected to a private docker network.
  -  Master containers can access the central server through a local
     proxy server which is both connected to the private docker network
     as the outside world. This proxy server also takes care of the
     encryption of the messages from the algorithms for the intended
     receiving organization.
  -  In case a single machine hosts multiple nodes, each node is
     attached to its own private Docker network.

-  **Temporary Volumes**

  -  Each algorithm mounts temporary volume, which is linked to the
     node and the ``run_id`` of the task
  -  The mounting target is specified in an environment variable
     ``TEMPORARY_FOLDER``. The algorithm can write anything to this
     directory.
  -  These volumes need to be cleaned manually.
     (``docker rm VOLUME_NAME``)
  -  Successive algorithms only have access to the volume if they share
     the same ``run_id`` . Each time a **user** creates a task, a new
     ``run_id`` is issued. If you need to share information between
     containers, you need to do this through a master container. If a
     master container creates a task, all slave tasks will obtain the
     same ``run_id``.

-  **RESTful API**

  -  All RESTful API output is HATEOS formatted.
      **(**\ `wiki <https://en.wikipedia.org/wiki/HATEOAS>`__\ **)**

-  **Local Proxy Server**

  -  Algorithm containers no longer receive an internet connection.
     They can only communicate with the central server through a local
     proxy service.
  -  It handles encryption for certain endpoints (i.e. ``/task``, the
     input or ``/result`` the results)

-  **Dockerized the Node**

  -  All node code is run from a Docker container. Build versions can
     be found at our Docker repository:
     ``harbor.distributedlearning.ai/infrastructure/node`` . Specific
     version can be pulled using tags.
  -  For each running node, a Docker volume is created in which the
     data, input and output is stored. The name of the Docker volume
     is: ``vantage-NODE_NAME-vol`` . This volume is shared with all
     incoming algorithm containers.
  -  Each node is attached to the public network and a private network:
     ``vantage-NODE_NAME-net``.
