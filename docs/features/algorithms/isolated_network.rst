Algorithm container isolation
-----------------------------

The algorithms run in vantage6 have access to the sensitive data that we want
to protect. Also, the algorithms may be built improperly, or may be outdated,
which might make it vulnerable to attacks. Therefore, one of the important
security measures that vantage6 implements is that all algorithms run in a
container that is not connected to the internet. The isolation from the internet
is achieved by starting the algorithm container is a Docker network that has no
internet access.

While the algorithm is thus isolated from the internet, it still has to be able
to access several different resources, such as the vantage6 server if it needs
to spawn other containers for subtasks. Such communication all takes place over
interfaces that are an integral part of vantage6, and are thus considered safe.
Below is a list of interfaces that are available to the algorithm container.

- The vantage6 server is available to the algorithm container via a proxy server
  running on the node.
- The VPN network is available to the algorithm container via the VPN client
  container.
- The SSH tunnel is available to the algorithm container via the SSH tunnel
  container.
- The whitelisted addresses are available to the algorithm container via the
  Squid proxy container.

Note that all of these connections are initiated from the algorithm container.
Vantage6 does not support incoming connections to the algorithm container.