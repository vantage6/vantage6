.. _hub-deployment:

Deployment
==========

The hub deployment should be done using vantage6 Helm charts in a Kubernetes
cluster. For small projects, the hub may also be deployed on a VM using ``microk8s``,
which is a lightweight Kubernetes distribution that is easy to install and use.

Helm charts
-----------

The hub can be deployed using the helm chart
``harbor2.vantage6.ai/chartrepo/infrastructure/hub``. This is the easiest way to deploy
the hub, as it will deploy all the necessary components together.

The hub chart is a parent of several subcharts. You can also deploy the subcharts
separately:

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

The hub chart configuration file contains the configuration of the subcharts, as well
as some global configuration.

The configuration file looks as followsand can be downloaded here:
:download:`hub_config.yaml <components/yaml/hub_config.yaml>`

.. literalinclude :: components/yaml/hub_config.yaml
    :language: yaml

The configuration of the subcharts is placed under the corresponding subchart key.
For example, the configuration of the authentication service is placed under the
``auth`` key. The full configuration options of the subcharts are described elsewhere
for the :ref:`auth <auth-configuration-file>`, :ref:`HQ <hq-configuration-file>`
and :ref:`algorithm store <algorithm-store-configuration-file>` components.

Deployment
----------

Once you have generated the configuration files, you can deploy the hub using the
command ``v6 hub start``. This command installs the ``hub`` Helm chart, which in turn
deploys HQ, authentication service and algorithm store as subcharts.

In some production environments, it may not be feasible to deploy the hub using the
CLI, for instance because Python is not available. In these cases, you can deploy the
hub using the Helm charts directly. The base commands are:

.. code-block:: bash

    # deploy full hub (HQ, auth, store)
    helm install my-hub-release hub --repo https://harbor2.vantage6.ai/chartrepo/infrastructure

    # or deploy the components individually (advanced usage)
    helm install my-hq-release hq --repo https://harbor2.vantage6.ai/chartrepo/infrastructure
    helm install my-auth-release auth --repo https://harbor2.vantage6.ai/chartrepo/infrastructure
    helm install my-store-release algorithm-store --repo https://harbor2.vantage6.ai/chartrepo/infrastructure

Of course, you may specify additional flags to the helm commands - see
the `helm documentation <https://helm.sh/docs/helm/helm_install>`_ for more information.

External databases
------------------

For production environments, it is recommended to use external PostgreSQL databases
instead of the databases deployed by the Helm charts. This provides better control over
database persistence, management, backups, and scaling.

Configuring external databases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When running ``v6 hub new``, you will be prompted for database URIs for the authentication
service, HQ, and the algorithm store (if enabled). The questionnaire will ask for:

- **Auth Database URI**: The connection string for the Keycloak authentication service database
- **HQ Database URI**: The connection string for the HQ (server) database
- **Algorithm Store Database URI**: The connection string for the algorithm store database

You should provide your own database URIs in the format:
``postgresql://username:password@host:port/database_name``

When deploying the hub, the database URIs must be accessible from within
the Kubernetes cluster. Use the actual hostname or IP address of your database server.
Ensure your Kubernetes cluster can access the database server.

.. note::

  You should create databases for the hub components before deploying the hub. The
  components will NOT create the databases for you.

Configuring access to the services
----------------------------------

For production environments, you still need to configure how traffic reaches the
hub components from the outside world. The hub chart provides an
Ingress configuration, but you can also bring your own routing solution.

.. note::

    For a local environment (using ``v6 sandbox``) or a development environment
    (using ``v6 dev``), access is configured automatically on your local machine.

Using the built-in Ingress
^^^^^^^^^^^^^^^^^^^^^^^^^^

The hub chart can create four ``Ingress`` resources - one for each public
endpoint:

* ``auth`` (Keycloak)
* ``hq`` (HQ API)
* ``portal`` (UI)
* ``store`` (algorithm store)

These are controlled via the ``hubIngress`` section in your hub values file
(:ref:`hub_config.yaml <hub-configuration-file>`). A minimal
example:

.. code-block:: yaml

   hubIngress:
     enabled: true
     hosts:
       auth: auth.example.org
       hq: hq.example.org
       portal: portal.example.org
       store: store.example.org
     tls:
       mode: cert-manager        # or: existingSecret
     certManager:
       enabled: true
       clusterIssuer: letsencrypt-prod

When ``hubIngress.enabled`` is ``true``, the hub chart:

* Creates ``Ingress`` resources for the components with the given hostnames.
* Terminates TLS at the Ingress (HTTP is used inside the cluster).
* Optionally provisions certificates using `cert-manager
  <https://cert-manager.io>`_ (``mode: cert-manager``), or reuses existing
  Kubernetes TLS secrets (``mode: existingSecret``).

When deploying via ``v6 hub start``, the CLI will do the following to ensure that
dependencies of the hub are installed and configured:

* Ensure the Keycloak operator (and its CRDs) are installed. This is required to deploy
  the Keycloak authentication service.
* When ``hubIngress.enabled`` is ``true``, ensure that a Kubernetes ingress
  controller is available. If no suitable controller is detected, ``v6 hub
  start`` will automatically install an `ingress-nginx
  <https://kubernetes.github.io/ingress-nginx/>`_ controller with a
  ``LoadBalancer`` service. You can find its public IP or hostname with:

  .. code-block:: bash

     kubectl get svc ingress-nginx-controller -n ingress-nginx

* When ``hubIngress.enabled`` is ``true`` and ``hubIngress.tls.mode`` is set to
  ``cert-manager``, ensure that the cert-manager CRDs are installed so that the
  ``Certificate`` resources rendered by the hub chart can be created. The
  cert-manager controller itself is expected to be managed by the platform or
  cluster administrator; if it is not detected, ``v6 hub start`` will emit a
  warning rather than attempting to install it automatically.

You can disable the automatic ingress controller installation using the
``--no-auto-install-ingress`` flag of ``v6 hub start`` and install/configure
your own ingress controller instead. The ``--ingress-class-name`` flag can be
used to override the ingress class name that should be used by the hub
ingresses. A situation in which you might want to do this is when you don't want
your hub endpoints to be publicly accessible.

If you already have an ingress controller and certificate management in place,
you can disable ``hubIngress`` and instead configure your own ``Ingress`` or
``LoadBalancer`` resources that route to the services exposed by the hub chart.

When using ``mode: cert-manager``, the hub chart will create ``Certificate``
resources for each public endpoint, and ``v6 hub start`` will ensure that the
cert-manager CRDs are present. The ClusterIssuer and cert-manager controller
that reconcile these Certificates should be provided by the cluster platform
or installed separately, according to your organization's standards.

Enabling TLS with cert-manager on AKS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The steps below summarize how to enable browser-trusted HTTPS for the hub
endpoints on AKS using cert-manager and Let's Encrypt.

1. **Install cert-manager (cluster admin action)**:

   .. code-block:: bash

      # Install CRDs (idempotent)
      kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.5/cert-manager.crds.yaml

      # Install controller, webhook and cainjector (client-side apply)
      kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.5/cert-manager.yaml

   Verify that the cert-manager pods are running:

   .. code-block:: bash

      kubectl -n cert-manager get deploy
      kubectl -n cert-manager get pods

2. **Create a ClusterIssuer** that matches the hub configuration. An example
   manifest is provided in this repository and can be downloaded here:
   :download:`clusterissuer-letsencrypt-prod.yaml <hub/clusterissuer-letsencrypt-prod.yaml>`.
   Adapt the ``email`` field and apply it:

   .. code-block:: bash

      kubectl apply -f /path/to/clusterissuer-letsencrypt-prod.yaml

   The issuer name (by default ``letsencrypt-prod``) must match
   ``hubIngress.certManager.clusterIssuer`` in your hub values file.

3. **Configure the hub to use cert-manager** by setting in your hub values:

   .. code-block:: yaml

      hubIngress:
        enabled: true
        tls:
          mode: cert-manager
        certManager:
          enabled: true
          clusterIssuer: letsencrypt-prod

   Ensure that the hostnames under ``hubIngress.hosts`` resolve publicly to the
   IP address of the ingress-nginx load balancer so that HTTP-01 challenges can
   succeed.

4. **Deploy or restart the hub**:

   .. code-block:: bash

      v6 hub start --name <your_hub> --user --local-chart-dir ./charts/

   The hub chart will create ``Certificate`` resources for the configured
   endpoints; cert-manager will obtain and renew the corresponding TLS
   certificates automatically. You can monitor progress with:

   .. code-block:: bash

      kubectl -n default get certificate
      kubectl -n default describe certificate <certificate-name>
