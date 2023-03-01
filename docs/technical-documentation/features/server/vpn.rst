VPN Server
----------

The VPN server is an optional component of the vantage6 infrastructure that
allows algorithms running on different nodes to communicate with one another.
Its implementation is discussed at length in this `paper <https://ebooks.iospress.nl/pdf/doi/10.3233/SHTI220682>`_.

The installation instructions for the VPN server are :ref:`here <eduvpn>`.

Now, when is the VPN server useful? The VPN server allows each node to establish
a VPN connection to the VPN server. The algorithm containers can use the VPN connection to communicate
with algorithm containers running on other nodes (provided those nodes have also
established a VPN connection). For each algorithm, the VPN IP address and one
or more ports with labels are stored in the database, which allows other
algorithm containers to find their contact details. This finally allows
algorithms to exchange information quickly without the need to go through the
central server for all communication.

.. todo::
  expand on this
