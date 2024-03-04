
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
