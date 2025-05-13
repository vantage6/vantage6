Whitelisting
------------

*Available since version 3.9.0*

Vantage6 algorithms are normally disconnected from the internet, and are
therefore unable to connect to access data that is not connected to the node
on node startup. Via this feature it is possible to whitelist certain domains,
ips and ports to allow the algorithm to connect to these resources. It is
important to note that only the http protocol is supported. If you require a
different protocol, please look at `SSH Tunnel`.

.. warning::

    As a node owner you are responsible for the security of your node. Make
    sure you understand the implications of whitelisting before enabling this
    feature.

    Be aware that when a port is whitelisted it is whitelisted for all domains
    and ips.

Setting up whitelisting
+++++++++++++++++++++++

Add block ``whitelist`` to the node configuration file:

.. code:: yaml

    whitelist:
        domains:
            - .google.com
            - github.com
            - host.docker.internal # docker host ip (windows/mac)
        ips:
            - 172.17.0.1 # docker bridge ip (linux)
            - 8.8.8.8
        ports:
            - 443

.. note::

    This feature makes use of Squid, which is a proxy server. For every domain,
    ip and port a `acl` directive is created. See
    `their <http://www.squid-cache.org/Doc/config/acl/>`_ documentation for
    more details on what valid values are.

Implementation details / Notes
++++++++++++++++++++++++++++++

The algorithm container is provided with the environment variables
``http_proxy``, ``HTTP_PROXY``, ``https_proxy``, ``HTTPS_PROXY``, ``no_proxy``
and ``NO_PROXY``. Unfortunately, there is no standard for handling these
variables. Therefore, whether this works will depend on the application you
are using. See `this <https://superuser.com/questions/944958/are-http-proxy-https-proxy-and-no-proxy-environment-variables-standard/1166790#1166790>`_
post for more details.

In case the algorithm tries to connect to a domain that is not whitelisted,
a http 403 error will be returned by the squid instance.

.. warning::

    Make sure the requests from the algorithm are using the environment
    variables. Some libraries will ignore these variables and use their own
    configuration.

    - The ``requests`` library will work for all cases.

    - The ``curl`` command will not work for vantage6 VPN addresses as the
      format of ``no_proxy`` variable is not supported. You can fix this by
      using the ``--noproxy`` option when requesting a VPN address.

.. note::

    VPN addresses in ``no_proxy`` have the same format as in the node
    configuration file, by default ``10.76.0.0/16``. Make sure the request
    library understands this format when connecting to a VPN address.




