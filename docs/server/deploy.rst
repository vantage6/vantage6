
.. _server-deployment:

Deploy
^^^^^^

The vantage6 server is a Flask application, that uses
`python-socketio <https://python-socketio.readthedocs.io>`_ for socketIO
connections. The server runs as a standalone process (listening on its own ip
address/port).

There are many deployment options. We simply provide a few examples.

-  :ref:`deploy-nginx`
-  :ref:`deploy-azure`
-  …

.. note::
    From version 3.2+ it is possible to horizontally scale the server (This
    upgrade is also made available to version 2.3.4)

    Documentation on how to deploy it will be shared here soon. Reach out to us
    on Discord for now.

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

.. note::
    We still have to document this. Reach out to us on Discord for now.

.. TODO
