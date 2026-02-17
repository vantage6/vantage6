.. _hub-deployment:

Deployment
==========

The hub deployment should be done using vantage6 Helm charts in a Kubernetes
cluster. For small projects, the hub may also be deployed on a VM using ``microk8s``,
which is a lightweight Kubernetes distribution that is easy to install and use.

Helm charts
-----------

The hub consists of several components. The following Helm charts are available to
deploy them:

- ``harbor2.vantage6.ai/chartrepo/infrastructure/hq``: Vantage6 HQ, UI, RabbitMQ, Prometheus.
- ``harbor2.vantage6.ai/chartrepo/infrastructure/auth``: Authentication service
- ``harbor2.vantage6.ai/chartrepo/infrastructure/algorithm-store``: Algorithm store

.. note::

    We recommend to use the latest version. Should you have reasons to
    deploy an older version use the helm chart. For instance, for version 5.0.0, use
    the chart ``https://harbor2.vantage6.ai/chartrepo/infrastructure/hq-5.0.0.tgz``
    for HQ, and similarly for the other components.

The image registry, mailserver and blob storage are optional components that cannot be
installed by vantage6. You have to install and deploy them yourself.


Configuration
-------------

To generate the appropriate configuration files, you can use ``v6 hub new``, as
described in the :ref:`use-hub` section.

Deployment
----------

Once you have generated the configuration files, you can deploy the hubusing the
command ``v6 hub start``. This command will deploy the hub using the Helm charts.

In some production environments, it may not be feasible to deploy the hub using the
CLI, for instance because Python is not available. In these cases, you can deploy the
hub using the Helm charts directly. The base commands to deploy HQ, authentication
service and algorithm store are:

.. code-block:: bash

    # deploy HQ
    helm install my-hq-release hq --repo https://harbor2.vantage6.ai/chartrepo/infrastructure

    # deploy authentication service
    helm install my-auth-release auth --repo https://harbor2.vantage6.ai/chartrepo/infrastructure

    # deploy algorithm store
    helm install my-store-release algorithm-store --repo https://harbor2.vantage6.ai/chartrepo/infrastructure

Of course, you may specify additional flags to the helm commands - see
the `helm documentation <https://helm.sh/docs/helm/helm_install>`_ for more information.

Configuring secrets
-------------------

To keep sensitive information secure, vantage6 uses Kubernetes Secrets.
The vantage6 CLI creates Kubernetes Secrets for credentials. If you don't use the CLI,
you should create the secrets in this section manually.

.. warning::

  Most Kubernetes secrets are currently created by the Helm chart based on the
  values.yaml file. This practice is not ideal because the secrets are stored in plain
  text in the values.yaml file. We will soon provide a way to create these secrets using
  the CLI as well (see
  `Issue #2391 <https://github.com/vantage6/vantage6/issues/2391>`_) - so the number of
  secrets in this section will increase soon.

Authentication chart (``auth``)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- **Purpose**: Store the keycloak admin username/password. Note that this is a different
  admin than the vantage6 admin - it is used to manage the Keycloak service.
- **Created by**: ``v6 auth new``
- **Reference in Helm values**: ``keycloak.auth.adminUserSecret``
- **Required keys**:

  - ``username``
  - ``password``

Configuring access to the services
----------------------------------

For production environments, you still need to configure routing traffic to the
hub. The helm charts do not include this configuration, as it is expected that you
will use your own routing solution.

.. note::

    For a local environment (using ``v6 sandbox``) or a development environment (using
    ``v6 dev``), access is configured automatically on your local machine.

We recommend that you specify an ``ingress`` or ``LoadBalancer`` service to set up
routing traffic to the services.

.. TODO add ingress example
.. TODO add LoadBalancer example
.. See issues #1686, #1948
