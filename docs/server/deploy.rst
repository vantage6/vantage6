.. _server-deployment:

Deployment
==========

.. _core-deployment:

Core
----

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
    socket messages get lost:

        * you should deploy a RabbitMQ service and configure the server to use it.
          :ref:`This section <rabbitmq-install>` explains how to do so.
        * you should ensure sticky sessions are enabled in your load balancer.

.. _deploy-nginx:

NGINX
"""""
Two examples are provided below. The first example shows how to configure NGINX with
a basic setup, which is suitable if you do not require the horizontal scaling feature.
The second example shows how to configure NGINX with sticky sessions.

.. note::

    SSL is not configured in these examples.

The most basic setup is to have a single backend server.

.. code:: nginx

    server {

        # Public port
        listen 80;
        server_name _;

        # vantage6-server. In the case you use a sub-path here, make sure
        # to forward also it to the proxy_pass
        location /subpath {
            include proxy_params;

            # internal ip and port
            proxy_pass http://127.0.0.1:7601/subpath;
        }

        # Allow the websocket traffic
        location /socket.io {
            include proxy_params;
            proxy_http_version 1.1;
            proxy_buffering off;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade";
            proxy_pass http://127.0.0.1:7601/socket.io/;
        }
    }



The following example shows how to configure NGINX where there are 3 backend servers
that are behind a load balancer. The load balancer is configured to use sticky sessions.



.. code:: nginx

   upstream backend {
       server backend1.example.com;
       server backend2.example.com;
       server backend3.example.com;

       sticky name=sessionid path=/;
   }

   server {

       # Public port
       listen 80;
       server_name _;

       # vantage6-server. In the case you use a sub-path here, make sure to forward also
       # it to the proxy_pass
       location /subpath {
           include proxy_params;

           # internal ip and port
           proxy_pass http://backend/subpath;
       }

       # Allow the websocket traffic
       location /socket.io {
           include proxy_params;
           proxy_http_version 1.1;
           proxy_buffering off;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "Upgrade";
           proxy_pass http://backend/socket.io/;
       }
   }

.. note::
    When you :ref:`server-configure` the server, make sure to include the ``/subpath``
    that has been set in the NGINX configuration into the ``api_path`` setting (e.g.
    ``api_path: /subpath/api``)

.. _deploy-docker-compose:

Docker compose
""""""""""""""

An alternative to ``v6 server start`` is to use docker-compose. Below is an
example of a ``docker-compose.yml`` file that may be used to start the server.
Obviously, you may want to change this to your own situation. For example, you
may want to use a different image tag, or you may want to use a different port.

.. code:: yaml

    services:
      vantage6-server:
        image: harbor2.vantage6.ai/infrastructure/server:cotopaxi
        ports:
        - "8000:80"
        volumes:
        - /path/to/my/server.yaml:/mnt/config.yaml
        command: ["/bin/bash", "-c", "/vantage6/vantage6-server/server.sh"]

If you wanted to set up a strong initial super user password, you can make use
of ``V6_INIT_SUPER_PASS_HASHED_FILE``. For this, your docker-compose file could
look something like this if you want to use `secrets in docker compose
<https://docs.docker.com/compose/use-secrets/>`_:

.. code:: yaml

    services:
      vantage6-server:
        image: harbor2.vantage6.ai/infrastructure/server:cotopaxi
        ports:
        - "8000:80"
        environment:
          # Set the path to the file containing the hashed password
          V6_INIT_SUPER_PASS_HASHED_FILE: /run/secrets/super-pass-hashed
          # Alternatively, you can also set the hashed password directly. Note that $s
          # must be escaped with another $.
          #V6_INIT_SUPER_PASS_HASHED: $$2b$$12$$...
        volumes:
        - /path/to/my/server.yaml:/mnt/config.yaml
        command: ["/bin/bash", "-c", "/vantage6/vantage6-server/server.sh"]
        secrets:
        - super-pass-hashed

    secrets:
        super-pass-hashed:
            file: /path/to/my/super-pass-hashed-root-only

To generate the hashed password, you can use the following script:

.. code:: python

    import getpass
    import bcrypt

    # read from stdin, to avoid having the password in the command history
    password = getpass.getpass().encode('utf-8')
    print(bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8'))

Or, if you prefer it in a one-liner:

.. code:: bash

    python3 -c "import getpass; import bcrypt; print(bcrypt.hashpw(getpass.getpass().encode('utf-8'), bcrypt.gensalt()).decode('utf-8'))" > /path/to/my/super-pass-hashed-root-only

.. note::

    Note that there might be better ways of passing a secret to your container.
    Especially if you are using some container orchestration tool like
    Kubernetes or Docker Swarm.
    If you use above method, do make sure root has exclusive read access to the
    file containing the hashed password.

.. TODO How to deploy on Azure app service



.. _algorithm-store-deployment:

Deploy
^^^^^^

The deployment of the algorithm store is highly similar to the deployment of
the vantage6 server. Both are Flask applications that are structured very
similarly.

The algorithm store's deployment is a bit simpler because it does not use
socketIO. This means that you don't have to take into account that the websocket
channels should be open, and makes it easier to horizontally scale the
application.

.. _deploy-algostore-nginx:

NGINX
"""""

The algorithm store can be deployed with a similar nginx script as detailed
for the :ref:`server <deploy-nginx>`.

One note is that for the algorithm store, the subpath is fixed at `/api`, so
be sure to set that in the subpath block.

.. _deploy-docker-compose:

Docker compose
""""""""""""""

The algorithm store can be started with ``v6 algorithm-store start``, but in
most deployment scenarios a docker-compose file is used. Below is an example
of a docker-compose file that can be used to deploy the algorithm store.

.. code:: yaml

    services:
      vantage6-algorithm-store:
        image: harbor2.vantage6.ai/infrastructure/algorithm-store:cotopaxi
        ports:
        - "8000:5000"
        volumes:
        - /path/to/my/server.yaml:/mnt/config.yaml
        command: ["/bin/bash", "-c", "/vantage6/vantage6-algorithm-store/server.sh"]

.. TODO How to deploy on Azure app service

Algorithm store
---------------

.. _install-algostore:

.. |instance-type| replace:: algorithm store
.. |requirements-link| replace:: :ref:`requirements <algorithm-store-requirements>`
.. |image| replace:: ``harbor2.vantage6.ai/infrastructure/algorithm-store``
.. |image-old| replace:: ``harbor2.vantage6.ai/infrastructure/algorithm-store:<VERSION>``
.. |deployment-link| replace:: :ref:`deployment <algorithm-store-deployment>`

.. include:: ../common/install.rst