.. _hub-deployment:

Deployment
==========

The hub deployment should be done using vantage6 Helm charts in a Kubernetes
cluster. For small projects, the hub may also be deployed on a VM using ``microk8s``,
which is a lightweight Kubernetes distribution that is easy to install and use.

Helm charts
-----------

Published charts live in GHCR as OCI Helm artifacts under the ``vantage6``
organization:

- ``oci://ghcr.io/vantage6/helm/hub``: parent chart (recommended)
- ``oci://ghcr.io/vantage6/helm/hq``: Vantage6 HQ, UI, RabbitMQ, Prometheus
- ``oci://ghcr.io/vantage6/helm/auth``: Authentication service (Keycloak)
- ``oci://ghcr.io/vantage6/helm/store``: Algorithm store

The ``hub`` chart is the easiest way to deploy everything together, since it installs
those components as subcharts. You can also install ``hq``, ``auth``, or ``store`` on
their own (advanced usage).

.. note::

    We recommend pinning the chart version explicitly (or using the CLI, which resolves
    the version for you). For example, for chart version ``5.0.0`` and HQ, run
    ``helm install my-hq oci://ghcr.io/vantage6/helm/hq --version 5.0.0``.
    Substitute ``hub``, ``auth``, or ``store`` for other components as needed.

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

    # deploy full hub (HQ, auth, store) — set CHART_VERSION to match the release
    helm install my-hub-release oci://ghcr.io/vantage6/helm/hub --version "${CHART_VERSION}"

    # or deploy the components individually (advanced usage)
    helm install my-hq-release oci://ghcr.io/vantage6/helm/hq --version "${CHART_VERSION}"
    helm install my-auth-release oci://ghcr.io/vantage6/helm/auth --version "${CHART_VERSION}"
    helm install my-store-release oci://ghcr.io/vantage6/helm/store --version "${CHART_VERSION}"

Of course, you may specify additional flags to the helm commands - see
the `helm documentation <https://helm.sh/docs/helm/helm_install>`_ for more information.

When deploying via ``v6 hub start``, the CLI carries out another set of checks and
installations to ensure that the hub is deployed correctly. This includes:

* Ensure the Keycloak operator (and its CRDs) are installed. This is required to deploy
  the Keycloak authentication service.
* When using the built-in gateway, ensure that an Envoy Gateway
  installation is available. If no suitable installation is detected,
  ``v6 hub start`` will automatically install Envoy Gateway (including the
  required Gateway API CRDs) into the cluster.
* When using the built-in gateway and ``hubGateway.tls.mode`` is set to
  ``cert-manager``, ensure that the cert-manager CRDs are installed so that the
  ``Certificate`` resources rendered by the hub chart can be created. The
  cert-manager controller itself is expected to be managed by the platform or
  cluster administrator; if it is not detected, ``v6 hub start`` will emit a
  warning rather than attempting to install it automatically.

For more details on the gateway and TLS configuration, see :ref:`gateway-configuration`.


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

  You should create databases for the hub components that you specified in the hub
  configuration file before deploying the hub. Vantage6 will NOT create the databases
  for you when using external databases.

.. _gateway-configuration:

Configuring access to the services
----------------------------------

For production environments, you still need to configure how your hub can be accessed
from the internet. The hub chart provides a built-in
Gateway API configuration (managed by an Envoy Gateway controller), but you
can also bring your own routing solution.

.. note::

    For a local environment (using ``v6 sandbox``) or a development environment
    (using ``v6 dev``), access is configured automatically on your local machine.

Using the built-in Gateway
^^^^^^^^^^^^^^^^^^^^^^^^^^

If the gateway is enabled, the hub chart will create one ``Gateway`` resource and four
``HTTPRoute`` resources - one for each public component:

* ``auth`` (Keycloak authentication service)
* ``hq`` (HQ)
* ``portal`` (UI)
* ``store`` (algorithm store)

These settings are controlled via the ``hubGateway`` section in your hub values file
(:ref:`hub_config.yaml <hub-configuration-file>`). A minimal
example:

If you already have your own Gateway API controller and certificate management
in place, you can disable ``hubGateway`` and instead configure your own
``Gateway``/ ``HTTPRoute``, ``Ingress`` or ``LoadBalancer`` resources that route to the
services exposed by the hub chart.

Enabling TLS with cert-manager
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The gateway can be configured to use cert-manager to issue and renew certificates. The
hub chart will then create ``Certificate``
resources for each public endpoint. In such cases, ``v6 hub start`` will ensure that the
cert-manager CRDs are present. The ClusterIssuer and cert-manager controller
that reconcile these Certificates should be provided by the cluster platform
or installed separately, according to your organization's standards.

The steps below summarize how to enable browser-trusted HTTPS for the hub
endpoints on your Kubernetes cluster using cert-manager and Let's Encrypt.

1. **Install cert-manager controller (cluster admin action)**:

   .. code-block:: bash

      # Ensure CRDs are present. You can do this manually, or let
      # ``v6 hub start`` apply them automatically when configured.
      kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.5/cert-manager.crds.yaml

      # Install controller, webhook and cainjector
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
   ``hubGateway.certManager.clusterIssuer`` in your hub values file.

3. **Configure the hub to use cert-manager** by setting in your hub values:

   .. code-block:: yaml

      hubGateway:
        enabled: true
        tls:
          mode: cert-manager
        certManager:
          enabled: true
          clusterIssuer: letsencrypt-prod

   Ensure that the hostnames under ``hubGateway.hosts`` resolve publicly to the
   IP address of the Gateway load balancer so that HTTP-01 challenges can
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
