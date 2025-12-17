.. _hub-deployment:

Deployment
==========

The server deployment should be done using the server's Helm chart in a Kubernetes
cluster. For small projects, the server may also be deployed on a VM using ``microk8s``,
which is a lightweight Kubernetes distribution that is easy to install and use.

By running the server's Helm chart, several services are deployed, that together make
up the core components of the vantage6 infrastructure. These services are:

- The server itself
- The user interface - for users to interact with the server
- The message broker (RabbitMQ) - to ensure node-server communication is reliable
.. TODO v5+ the database should NOT be part of the server always - this should be
.. optional
- The database (PostgreSQL) - to store the server's data

Configuration
-------------

When deploying the server, you should also deploy the authentication service (Keycloak)
and optionally (but recommended) the algorithm store. It is recommended that you first
generate configuration files for the server, authentication service and algorithm store
using the following commands:

- ``v6 server new``
- ``v6 auth new``
- ``v6 algorithm-store new``

These commands will generate the necessary configuration files.

Deployment
----------

Once you have generated the configuration files, you can deploy the server using the
command ``v6 server start``. This command will deploy the server using the Helm chart.

In some production environments, it may not be feasible to deploy the server using the
CLI, for instance because Python is not available. In these cases, you can deploy the
server using the Helm chart directly. The base command to deploy the server, auth and
algorithm store is:

.. code-block:: bash

    # install server
    helm install my-server-release server --repo https://harbor2.vantage6.ai/chartrepo/infrastructure

    # install auth
    helm install my-auth-release auth --repo https://harbor2.vantage6.ai/chartrepo/infrastructure

    # install algorithm store
    helm install my-store-release algorithm-store --repo https://harbor2.vantage6.ai/chartrepo/infrastructure

Of course, you may want to specify additional flags to the helm commands - see
the `helm documentation <https://helm.sh/docs/helm/helm_install>`_ for more information.

Configuring access to the services
----------------------------------

For production environments, you still need to configure routing traffic to the
server, auth and algorithm store. The helm charts do not include this configuration,
as it is expected that you will use your own routing solution.

.. note::

    For a local environment (using ``v6 sandbox``) or a development environment (using
    ``v6 dev``), access is configured automatically on your local machine.

We recommend that you specify an ``ingress`` or ``LoadBalancer`` service to set up
routing traffic to the services.

.. TODO v5+ add ingress example
.. TODO v5+ add LoadBalancer example
