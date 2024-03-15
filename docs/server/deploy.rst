
.. _server-deployment:

Deploy
^^^^^^

The vantage6 server is a Flask application, that uses
`python-socketio <https://python-socketio.readthedocs.io>`_ for socketIO
connections. The server runs as a standalone process (listening on its own ip
address/port).

There are many deployment options. We simply provide a few examples.

-  :ref:`deploy-nginx`
-  :ref:`deploy-docker-compose`
-  …

.. note::
    Because the server uses socketIO to exchange messages with the nodes and
    users, it is not trivial to horizontally scale the server. To prevent that
    socket messages get lost, you should deploy a RabbitMQ service and configure
    the server to use it. :ref:`This section <rabbitmq-install>` explains how to
    do so.

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

.. _deploy-docker-compose:

Docker compose
""""""""""""""

An alternative to ``v6 server start`` is to use docker-compose. Below is an
example of a ``docker-compose.yml`` file that may be used to start the server.
Obviously, you may want to change this to your own situtation. For example, you
may want to use a different image tag, or you may want to use a different port.

.. code:: yaml

    services:
      vantage6-server:
        image: harbor2.vantage6.ai/infrastructure/server:cotopaxi
        ports:
        - "8000:5000"
        volumes:
        - /path/to/my/server.yaml:/mnt/config.yaml
        command: ["/bin/bash", "-c", "/vantage6/vantage6-server/server.sh"]

.. TODO How to deploy on Azure app service
