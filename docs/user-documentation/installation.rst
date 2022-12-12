.. include:: <isonum.txt>

.. _install_vantage6:

Installation
============

**vantage6** consists of several :ref:`components <Components>` that
can be installed. Which component(s) you need depends on your use case.
Also the requirements differ per component.

.. _requirements:

Requirements
------------

Client
^^^^^^

You can interact with the server via the API. You can explore the server
API on ``https://<serverdomain>/apidocs``
(e.g. https://petronas.vantage6.ai/apidocs for our Petronas server).

You can use any language to interact with the server as long as it
supports HTTP requests. For Python and R we have written wrappers to
simplify the interaction with the server: see the :ref:`client install`
for more details on how to install these.

.. warning::
    Depending on your algorithm it *may* be required to use a specific
    language to post a task and retrieve the results. This could happen when
    the output of an algorithm contains a language specific datatype and or
    serialization.

    E.g. when the algorithm is written in R and the output is written back
    in RDS (=specific to R) you would also need R to read the final input.

    **Please consult the documentation of the algorithm you want to use if
    this is the case.**

Node & Server
^^^^^^^^^^^^^

The (minimal) requirements of the node and server are similar. Note that
not all of these are hard requirements: it could well be that it also
works on other hardware, operating systems, versions of Python etc.

**Hardware**

-  x86 CPU architecture + virtualization enabled
-  1 GB memory
-  50GB+ storage
-  Stable and fast (1 Mbps+ internet connection)
-  Public IP address

**Software**

-  Operating system

   -  Ubuntu 18.04+ or
   -  MacOS Big Sur+ or
   -  Windows 10+

-  :ref:`python`
-  :ref:`docker`

.. warning::
    The hardware requirements of the node also depend on the algorithms that
    the node will run. For example, you need much less compute power for a
    descriptive statistical algorithm than for a machine learning model.

.. _python:

Python
""""""

Installation of any of the **vantage6** packages requires Python 3.7.
For installation instructions, see `python.org <https://python.org>`__,
`anaconda.com <https://anaconda.com>`__ or use the package manager
native to your OS and/or distribution.

.. note::
    We recommend you install **vantage6** in a new, clean Python (Conda)
    environment.

    Other version of Python >= 3.6 will most likely also work, but may give
    issues with installing dependencies. For now, we test vantage6 on
    version 3.7, so that is a safe choice.

.. _docker:

Docker
""""""

..  warning::

    Note that for **Linux**, some `post-installation
    steps <https://docs.docker.com/engine/install/linux-postinstall/>`__ may
    be required. Vantage6 needs to be able to run docker without ``sudo``,
    and these steps ensure just that.

Docker facilitates encapsulation of applications and their dependencies
in packages that can be easily distributed to diverse systems.
Algorithms are stored in Docker images which nodes can download and
execute. Besides the algorithms, both the node and server are also
running from a docker container themselves.

Please refer to `this page <https://docs.docker.com/engine/install/>`__
on how to install Docker. To verify that Docker is installed and running
you can run the ``hello-world`` example from Docker.

.. code:: bash

   docker run hello-world

.. note::

    * Always make sure that Docker is running while using vantage6!
    * We recommend to always use the latest version of Docker.

.. _client install:

Client
------

We provide four ways in which you can interact with the server to manage
your vantage6 resources: the user interface (UI), the
:ref:`Python client <python client library>`, the
:ref:`R client <r client library>`, and the server API.

What you need to install depends on which interface you choose. In order
to use the UI or the server API, you usually don’t need to install
anything: the UI is a website, and the API can be called via HTTP
requests from a programming language of your choice. For the UI, you
only need to set it up in case you are setting up your own server (see
:ref:`UI` for instructions).

Installation instructions for the Python client and R client are below.
For most use cases, we recommend to use the UI (for anything except
creating tasks) and/or the Python Client (which covers server API
functionality completely).

Python client library
^^^^^^^^^^^^^^^^^^^^^

Before you install the Python client, we check the version of the server you
are going to interact with first. The easiest way of doing that is checking
the ``/version`` endpoint of the server you are going to use on
``https://<server_url>/version`` (e.g. `https://petronas.vantage6.ai/version`
or `http://localhost:5000/api/version`).

Then you can install the ``vantage6-client`` with:

::

   pip install vantage6==<version>

where you add the version you want to install. You may also leave out
the version to install the most recent version.

.. _r client install:

R client library
^^^^^^^^^^^^^^^^

The R client currently only supports creating tasks and retrieving their
results. It can not (yet) be used to manage resources, such as creating
and deleting users and organizations.

You can install the R client by running:

.. code:: r

   devtools::install_github('IKNL/vtg', subdir='src')


.. _install-node:

Node
----

To install the **vantage6-node** make sure you have met the
:ref:`requirements <requirements>`. Then install the latest version:

::

   pip install vantage6

This will install the CLI in order to configure, start and stop the node. The
node software itself will be downloaded when you start the node for the first
time.


.. _install-server:

Server
------

Local Installation
^^^^^^^^^^^^^^^^^^
This installs the *vantage6-server* at an VM or your local machine. To install
the *vantage6-server* make sure you have met the :ref:`requirements`. Then
install the latest version:

::

   pip install vantage6

This command will install the vantage6 command line interface (CLI),
from which you can create new servers (see :ref:`Use Server <use-server>`).

Cloud Service Provider
^^^^^^^^^^^^^^^^^^^^^^
To install vantage6 at a cloud service provider you can use a Docker Image
(This is the same image used by ``vserver COMMAND``). If you are using a VM,
you can follow the instructions for :ref:`local installation` and check
our :ref:`server-deployment`.

Depending on the ``VERSION``, you can use

::

    harbor2.vantage6.ai/infrastructure/server:VERSION


See our :ref:`Release Strategy <release-strategy>` for selecting the right
``VERSION``. E.g.:

* ``petronas`` |rarr| version 3.x.x, is updated on reboot and will contain the
  latest security updates
* ``2.3.4`` |rarr| exact version, will not be changed on reboot


Optional components
^^^^^^^^^^^^^^^^^^^
There are several optional components that you can set up apart from the
vantage6-server itself.

:ref:`UI`
  A web application that will allow your users to interact more easily with
  your vantage6 server.

:ref:`eduvpn`
  If you want to enable algorithm containers that are running on different
  nodes, to directly communicate with one another, you require a VPN
  server. Refer to on how to install the VPN server.

:ref:`rabbitmq`
  If you have a server with a high workload whose performance you want to
  improve, you may want to set up a RabbitMQ service which enables horizontal
  scaling of the Vantage6 server.

:ref:`docker-registry`
  A docker registry can be used to store algorithms but it is also
  possible to use `Docker hub <https://hub.docker.com/>`__ for this.


.. _UI:

User Interface
""""""""""""""

.. todo:: I think we also have a Docker container for this now?

The User Interface (UI) is a web application that aims to make it easy
to interact with the server. It allows you to manage all your resources
(such as creating collaborations, editing users, or viewing tasks),
except for creating new tasks. We aim to incorporate this functionality
in the near future.

If you plan on deploying your own server and want to use the UI, follow
the installation instructions on the UI `Github
page <https://github.com/vantage6/vantage6-UI>`__. The UI is an Angular
application and as such, you may be required to install *Node.js.* Once
you have deployed the UI to the internet, any user that is registered on
your vantage6 server will be able to use it.

The UI is not compatible with older versions (<3.3) of vantage6.

If you plan on using the existing Petronas server, you can simply go to
https://portal.petronas.vantage6.ai and login with your user account.

.. figure:: /images/screenshot_ui.png
    :alt: UI screenshot
    :align: center

    Screenshot of the vantage6 UI


.. _eduvpn:

EduVPN
""""""

*Please note that EduVPN is an* \ **optional**\  *component. It enables
the use of advanced algorithms that require node-to-node communication.*

`EduVPN <https://www.eduvpn.org/>`_ provides an API for the OpenVPN
server, which is required for automated certificate retrieval by the
nodes. Like vantage6, it is an open source platform.

.. note::
    We are considering to eliminate the need for an EduVPN server by
    implementing a vantage6 API for OpenVPN.

The following documentation shows you how to install EduVPN:

-  `Debian <https://github.com/eduvpn/documentation/blob/v2/DEPLOY_DEBIAN.md>`__
-  `Centos <https://github.com/eduvpn/documentation/blob/v2/DEPLOY_CENTOS.md>`__
-  `Fedora <https://github.com/eduvpn/documentation/blob/v2/DEPLOY_FEDORA.md>`__

After the installation is done, you need to configure the server to:

1. Enable client-to-client communication. This can be achieved in the
   configuration file by the ``clientToClient`` setting (see
   `here <https://github.com/eduvpn/documentation/blob/v2/PROFILE_CONFIG.md>`__).
2. Do not block LAN communication (set ``blockLan`` to ``false``). This
   allows your docker subnetworks to continue to communicate, which is
   required for vantage6 to function normally.
3. Enable `port
   sharing <https://github.com/eduvpn/documentation/blob/v2/PORT_SHARING.md>`__
   (Optional). This may be useful if the nodes are behind a strict
   firewall. Port sharing allows nodes to connect to the VPN server only
   using outgoing ``tcp/443``. Be aware that `TCP
   meltdown <https://openvpn.net/faq/what-is-tcp-meltdown/>`__ can occur
   when using the TCP protocol for VPN.
4. Create an application account.

.. warning::
    EduVPN allows to listen to multiple protocols (UDP/TCP) and ports at the
    same time. Be aware that all nodes need to be connected using the same
    protocol and port in order to communicate with each other.

**Example configuration**

The following configuration makes a server
listens to ``TCP/443`` only. Make sure you set ``clientToClient`` to
``true`` and ``blockLan`` to ``false``. The ``range`` needs to be supplied to
the node configuration files. Also note that the server configured below
uses
`port-sharing <https://github.com/eduvpn/documentation/blob/v2/PORT_SHARING.md>`__.

.. raw:: html

   <details>
   <summary><a>EduVPN server configuration</a></summary>

.. code:: php

   // /etc/vpn-server-api/config.php
   <?php

   return [
       // List of VPN profiles
       'vpnProfiles' => [
           'internet' => [
               // The number of this profile, every profile per instance has a
               // unique number
               // REQUIRED
               'profileNumber' => 1,

               // The name of the profile as shown in the user and admin portals
               // REQUIRED
               'displayName' => 'vantage6 :: vpn service',

               // The IPv4 range of the network that will be assigned to clients
               // REQUIRED
               'range' => '10.76.0.0/16',

               // The IPv6 range of the network that will be assigned to clients
               // REQUIRED
               'range6' => 'fd58:63db:3245:d20d::/64',

               // The hostname the VPN client(s) will connect to
               // REQUIRED
               'hostName' => 'eduvpn.vantage6.ai',

               // The address the OpenVPN processes will listen on
               // DEFAULT = '::'
               'listen' => '::',

               // The IP address to use for connecting to OpenVPN processes
               // DEFAULT = '127.0.0.1'
               'managementIp' => '127.0.0.1',

               // Whether or not to route all traffic from the client over the VPN
               // DEFAULT = false
               'defaultGateway' => true,

               // Block access to local LAN when VPN is active
               // DEFAULT = false
               'blockLan' => false,

               // IPv4 and IPv6 routes to push to the client, only used when
               // defaultGateway is false
               // DEFAULT = []
               'routes' => [],

               // IPv4 and IPv6 address of DNS server(s) to push to the client
               // DEFAULT  = []
               // Quad9 (https://www.quad9.net)
               'dns' => ['9.9.9.9', '2620:fe::fe'],

               // Whether or not to allow client-to-client traffic
               // DEFAULT = false
               'clientToClient' => true,

               // Whether or not to enable OpenVPN logging
               // DEFAULT = false
               'enableLog' => false,

               // Whether or not to enable ACLs for controlling who can connect
               // DEFAULT = false
               'enableAcl' => false,

               // The list of permissions to allow access, requires enableAcl to
               // be true
               // DEFAULT  = []
               'aclPermissionList' => [],

               // The protocols and ports the OpenVPN processes should use, MUST
               // be either 1, 2, 4, 8 or 16 proto/port combinations
               // DEFAULT = ['udp/1194', 'tcp/1194']
               'vpnProtoPorts' => [
                   'tcp/1195',
               ],

               // List the protocols and ports exposed to the VPN clients. Useful
               // for OpenVPN port sharing. When empty (or missing), uses list
               // from vpnProtoPorts
               // DEFAULT = []
               'exposedVpnProtoPorts' => [
                   'tcp/443',
               ],

               // Hide the profile from the user portal, i.e. do not allow the
               // user to choose it
               // DEFAULT = false
               'hideProfile' => false,

               // Protect to TLS control channel with PSK
               // DEFAULT = tls-crypt
               'tlsProtection' => 'tls-crypt',
               //'tlsProtection' => false,
           ],
       ],

       // API consumers & credentials
       'apiConsumers' => [
           'vpn-user-portal' => '***',
           'vpn-server-node' => '***',
       ],
   ];


.. raw:: html

   </details>

The following configuration snippet can be used to add an API
user. The username and the ``client_secret`` have to be added to the
vantage6-server configuration file.

.. raw:: html

   <details>
   <summary><a>Add a VPN server user account</a></summary>

.. code:: php

   ...
   'Api' => [
     'consumerList' => [
       'vantage6-user' => [
         'redirect_uri_list' => [
           'http://localhost',
         ],
         'display_name' => 'vantage6',
         'require_approval' => false,
         'client_secret' => '***'
       ]
     ]
   ...

.. raw:: html

   </details>


.. _rabbitmq:

RabbitMQ
""""""""


*Please note that RabbitMQ is an* \ **optional**\  *component. It enables
the server to handle multiple requests at the same time. This is
important if a server has a high workload.*

There are several options to host your own RabbitMQ server. You can run
`RabbitMQ in Docker <https://hub.docker.com/_/rabbitmq>`__ or host
`RabbitMQ on
Azure <https://www.golinuxcloud.com/install-rabbitmq-on-azure/>`__. When
you have set up your RabbitMQ service, you can connect the server to it
by adding the following to the server configuration:

::

   rabbitmq_uri: amqp://<username>:<password@<hostname>:5672/<vhost>

Be sure to create the user and vhost that you specify exist! Otherwise,
you can add them via the `RabbitMQ management
console <https://www.cloudamqp.com/blog/part3-rabbitmq-for-beginners_the-management-interface.html>`__.

.. _docker-registry:

Docker registry
"""""""""""""""

A Docker registry or repository provides storage and versioning for Docker
images. Installing a private Docker registry can be useful if you want
to securely host your own algorithms.

Docker Hub
~~~~~~~~~~

Docker itself provides a registry as a turn-key solution on Docker Hub.
Instructions for setting it up can be found here:
https://hub.docker.com/_/registry.

Harbor
~~~~~~

`Harbor <https://goharbor.io>`_ is another option for running a
registry. Harbor provides access control, a user interface and automated
scanning on vulnerabilities.


.. _server-deployment:

Deployment
^^^^^^^^^^

The *vantage6-server* uses Flask as backbone, together with
`python-socketio <https://python-socketio.readthedocs.io>`_ for websocket
support. The server runs as a standalone process (listening on its own ip
address/port).

.. info::
    From version 3.2+ it is possible to horizontally scale the server (This
    upgrade is also made available to version 2.3.4)

    Documentation on how to deploy it will be shared here. Reach out to us
    on Discord for now.

There are many deployment options, so these examples are not complete
and exhaustive.

-  :ref:`deploy-nginx`
-  :ref:`deploy-azure`
-  …

.. _deploy-nginx:

NGINX
"""""

A basic setup is shown below. Note that SSL is not configured in this example.

.. code:: nginx

   server {

       # Public port
       listen 80;
       server_name _;

       # vantage6-server. In the case you use a sub-path here, make sure
       # to foward also it to the proxy_pass
       location /subpath {
           include proxy_params;

           # internal ip and port
           proxy_pass http://127.0.0.1:5000/subpath;
       }

       # Allow the websocket traffic
       location /socket.io {
           include proxy_params;
           proxy_http_version 1.1;
           proxy_buffering off;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "Upgrade";
           proxy_pass http://127.0.0.1:5000/socket.io;
       }
   }

.. note::
    When you :ref:`server-configure` the server, make
    sure to include the ``/subpath`` that has been set in the NGINX
    configuration into the ``api_path`` setting
    (e.g. ``api_path: /subpath/api``)

.. _deploy-azure:

Azure app service
"""""""""""""""""

TODO

.. _server-logging: