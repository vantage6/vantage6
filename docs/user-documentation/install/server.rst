Server
======

To install the **vantage6-server** make sure you have met the
:ref:`requirements`. Then install the
latest version:

::

   pip install vantage6

This command will install the vantage6 command line interface (CLI),
from which you can create new servers (see Use
`running-the-server <../../usage/running-the-server/>`__).

.. todo
    Fix the link above!

**Optional components**

There are several optional components that you can set up apart from the
vantage6-server itself.

- You can set up a :ref:`UI`, which is a
  web application that will allow your users to communicate more easily
  with your vantage6 server.

- If you want to enable algorithm containers that are running on different
  nodes, to directly communicate with one another, you require a VPN
  server. Refer to :ref:`eduvpn` on how to install the VPN
  server.

- If you have a server with a high workload whose performance you want to
  improve, you may want to set up a RabbitMQ service which enables
  horizontal scaling of the Vantage6 server.
  See :ref:`rabbitmq` on how to set this up.

- A docker registry can be used to store algorithms but it is also
  possible to use `Docker hub <https://hub.docker.com/>`__ for this. For
  instructions on how to install your own Docker registry see
  :ref:`docker-registry`.


.. _UI:

User Interface
^^^^^^^^^^^^^^

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
^^^^^^

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
^^^^^^^^


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
^^^^^^^^^^^^^^^

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

