SSH Tunnel
----------

*Available since version 3.7.0*

Vantage6 algorithms are normally disconnected from the internet, and are
therefore unable to connect to access data that is not connected to the node
on node startup. Via this feature, however, it is possible to connect to a
remote server through a secure SSH connection. This allows you to connect to
a dataset that is hosted on another machine than your node, as long as you
have SSH access to that machine.

An alternative solution would be to create a `whitelist <whitelisting>`_ of domains, ports and
IP addresses that are allowed to be accessed by the algorithm.

Setting up SSH tunneling
++++++++++++++++++++++++

1. Create a new SSH key pair
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a new key pair *without* a password on your node machine. To do this,
enter the command below in your terminal, and leave the password empty when
prompted.

.. code:: bash

    ssh-keygen -t rsa

You are required not to use a password for the private key, as vantage6 will
set up the SSH tunnel without user intervention and you will therefore not
be able to enter the password in that process.

2. Add the public key to the remote server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Copy the contents of the public key file (``your_key.pub``) to the remote
server, so that your node will be allowed to connect to it. In the most common
case, this means adding your public key to the ``~/.ssh/authorized_keys`` file
on the remote server.

3. Add the SSH tunnel to your node configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

An example of the SSH tunnel configuration can be found below. See
:ref:`here <node-configure-structure>` for a full example of a node
configuration file.

.. code:: yaml

  databases:
    httpserver: http://my_http:8888
  ssh-tunnels:
    - hostname: my_http
      ssh:
        host: my-remote-machine.net
        port: 22
        fingerprint: "ssh-rsa AAAAE2V....wwef987vD0="
        identity:
          username: bob
          key: /path/to/your/private/key
      tunnel:
        bind:
          ip: 0.0.0.0
          port: 8888
        dest:
          ip: 127.0.0.1
          port: 9999

There are a few things to note about the SSH tunnel configuration:

1. You can provide multiple SSH tunnels in the ``ssh-tunnels`` list, by simply
   extending the list.
2. The hostname of each tunnel should come back in one of the databases, so
   that they may be accessible to the algorithms.
3. The ``host`` is the address at which the remote server can be reached. This
   is usually an IP address or a domain name. Note that you are able to specify
   IP addresses in the local network. Specifying non-local IP addresses is not
   recommended, as you might be exposing your node if the IP address is spoofed.
4. The ``fingerprint`` is the fingerprint of the remote server. You can usually
   find it in `/etc/ssh/ssh_host_rsa_key.pub` on the remote server.
5. The ``identity`` section contains the username and path to the private key
   your node is using. The username is the username you use to log in to the
   remote server, in the case above it would be ``ssh bob@my-remote-machine.net``.
6. The ``tunnel`` section specifies the port on which the SSH tunnel will be
   listening, and the port on which the remote server is listening. In the
   example above, on the remote machine, there would be a service listening
   on port 9999 on the machine itself (which is why the IP is 127.0.0.1 a.k.a.
   localhost). The tunnel will be bound to port 8888 on the node machine, and
   you should therefore take care to include the correct port in your database
   path.


Using the SSH tunnel
++++++++++++++++++++

How you should use the SSH tunnel depends on the service that you are running
on the other side. In the example above, we are running a HTTP server and
therefore we should obtain data via HTTP requests. In the case of a SQL service,
one would need to send SQL queries to the remote server instead.

.. note::
    We aim to extend this section later with an example of an algorithm that
    is using this feature.