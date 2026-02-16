.. _node-whitelisting:

Whitelisting
------------

*Available since version 3.9.0*

Vantage6 algorithms are normally disconnected from the internet, and are
therefore unable to connect to access data that is not connected to the node
on node startup. Via this feature it is possible to whitelist certain Kubernetes
services and IP addresses to allow the algorithm to connect to these resources.

.. warning::

    As a node owner you are responsible for the security of your node. Make
    sure you understand the implications of whitelisting before enabling this
    feature.


Setting up whitelisting
+++++++++++++++++++++++

The :ref:`node configuration file example <node-configure-structure>` contains a
``whitelist`` section that can be used to configure the whitelisting. That section
explains the different options that are available.
