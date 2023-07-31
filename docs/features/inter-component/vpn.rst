Algorithm-to-algorithm comunication
-----------------------------------

*Since version 3.0.0*

Originally, all communication in the vantage6 infrastructure occurs via the
central server. Algorithms and nodes could not directly communicate with one
another. Since version 3.0.0, algorithms can communicate with one another
directly, without the need to go through the central server. This is achieved
by connecting the nodes to a `VPN network <https://en.wikipedia.org/wiki/Virtual_private_network>`_.

The implementation of algorithm-to-algorithm communication in vantage6 is
discussed at length in this `paper <https://ebooks.iospress.nl/pdf/doi/10.3233/SHTI220682>`_.

When to use
^^^^^^^^^^^

Some algorithms require a lot of communication between algorithm containers
before a solution is achieved. For example, there are algorithms that uses
iterative methods to optimize a solution, or algorithms that share partial
machine learning models with one another in the learning process.

For such algorithms, using the default communication method (via the central
server) can be very inefficient. Also, some popular libraries assume that direct
communication between algorithm containers is possible. These libraries would
have to be adapted specifically for the vantage6 infrastructure, which is not
always feasible. In such cases, it is better to setup a VPN connection to
allow algorithm containers to communicate directly with one another.

Another reason to use a VPN connection is that for some algorithms, routing
all partial results through the central server can be undeseriable. For example,
with many algorithms using an `MPC <https://en.wikipedia.org/wiki/Secure_multi-party_computation>`_
protocol, it may be possible for the central party to reconstruct the original
data if they have access to all partial results.

How to use
^^^^^^^^^^

In order to use a VPN connection, a VPN server must be set up, and the vantage6
server and nodes must be configured to use this VPN server. Below we detail How
this can be done.

Installing a VPN server
+++++++++++++++++++++++

To use algorithm-to-algorithm communication, a VPN server must be set up by
the server administrator. The installation instructions for the VPN server
are :ref:`here <eduvpn>`.

Configuring the vantage6 server
+++++++++++++++++++++++++++++++

The vantage6 server must be configured to use the VPN server. This is done by
adding the following configuration snippet to the configuration file.

.. code:: yaml

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

Note that the vantage6 server does not connect to the VPN server itself. It uses
the configuration above to provide nodes with a VPN configuration file when they
want to connect to VPN.

Configuring the vantage6 node
+++++++++++++++++++++++++++++

A node administrator has to configure the node to use the VPN server. This is
done by adding the following configuration snippet to the configuration file.

.. code:: yaml

  vpn_subnet: '10.76.0.0/16'

This snippet should include the subnet on which the node will connect to the
VPN network, and should be part of the subnet range of the VPN server. Node
administrators should consult the VPN server administrator to determine which
subnet range to use.

If all configuration is properly set up, the node will automatically connect
to the VPN network on startup.

.. warning::
    If the node fails to connect to the VPN network, the node will not stop.
    It will print a warning message and continue to run.

.. note::
    Nodes that connect to a vantage6 server with VPN do not necessarily have to
    connect to the VPN server themselves: they may be involved in a
    collaboration that does not require VPN.

How to test the VPN connection
++++++++++++++++++++++++++++++

`This algorithm <https://github.com/vantage6/v6-node-to-node-diagnostics>`_ can
be used to test the VPN connection. The script `test_on_v6.py` in this
repository can be used to send a test task which will print whether echoes over
the VPN network are working.

Use VPN in your algorithm
+++++++++++++++++++++++++

If you are using the Python algorithm client, you can call the following
function:

.. code:: python

    client.vpn.get_addresses()

which will return a dictionary containing the VPN IP address and port of each
of the algorithms running that task.

.. warning::
    If you are using the old algorithm client ``ContainerClient`` (which is
    the default in vantage6 3.x), you should use
    ``client.get_algorithm_addresses()`` instead.

If you are not using the algorithm client, you can send a request to
to the endpoint ``/vpn/algorithm/addresses`` on the vantage6 server (via the
node proxy server), which will return a dictionary containing the VPN IP address
and port of each of the algorithms running that task.

How does it work?
^^^^^^^^^^^^^^^^^

As mentioned before, the implementation of algorithm-to-algorithm communication is
discussed at length in this `paper <https://ebooks.iospress.nl/pdf/doi/10.3233/SHTI220682>`_.
Below, we will give a brief overview of the implementation.

On startup, the node requests a VPN configuration file from the vantage6 server.
The node first checks if it already has a VPN
configuration file and if so, it will try to use that. If connecting with the
existing configuration file fails, it will try to renew the configuration file's
keypair by calling ``/vpn/update``. If that fails, or if no configuration file
is present yet (e.g. on first startup of a node), the node will request a new
configuration file by calling ``/vpn``.

The VPN configuration file is an ``.ovpn`` file that is passed to a VPN client
container that establishes the VPN connection. This VPN client container keeps
running in the background for as long as the node is running.

When the VPN client container is started, a few network rules are changed on
the host machine to forward the incoming traffic on the VPN subnet to the VPN
client container. This is necessary because the VPN traffic will otherwise
never reach the vantage6 containers. The VPN client container is configured
to drop any traffic that does not originate from the VPN connection.

When a task is started, the vantage6 node determines how many ports that
particular algorithm requires on the local Docker network. It determines which
ports are available and then assigns those ports to the algorithm. The node
then stores the VPN IP address and the assigned ports in the database. Also,
it configures the local Docker network such that the VPN client container
forwards all incoming traffic for algorithm containers to the right port on
the right algorithm container. *Vice versa*, the VPN client container is
configured to forward outgoing traffic over the VPN network to the right
addresses.

Only when the all this configuration is completed, is the algorithm container
started.

