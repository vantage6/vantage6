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
   node-configuration file. You can specify a list of regex expressions here.
   Some examples of what you could define:

   1. ``^harbor2.vantage6.ai/[a-zA-Z]+/[a-zA-Z]+``: allow all images
      from the vantage6 registry
   2. ``^harbor2.vantage6.ai/algorithms/glm``: only allow the GLM image, but
      all builds of this image
   3. ``^harbor2.vantage6.ai/algorithms/glm@sha256:82becede498899ec668628e7cb0ad87b6e1c371cb8``
      ``a1e597d83a47fac21d6af3``: allows only this specific build from the GLM
      image to run on your data

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
