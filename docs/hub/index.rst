.. include:: <isonum.txt>

.. _hub-admin-guide:

Hub admin guide
==================

The vantage6 hub is the collection of all central components of the vantage6
infrastructure - so everything that is not a node. The hub contains both components
based on vantage6 software, such as vantage6 HQ and the user interface, as well as
components based on external software, such as the authentication service (Keycloak)and
monitoring (Prometheus). Below, each of the components is listed and explained.

Required components
^^^^^^^^^^^^^^^^^^^

:ref:`Vantage6 HQ <hub-admin-guide-hq>`
  The vantage6 HQ is the core component of the vantage6 infrastructure.
  It is responsible for managing the nodes and tasks.

:ref:`Authentication <hub-admin-guide-auth>`
  Vantage6 authentication is managed through a separate
  `Keycloak <https://www.keycloak.org/>`_ service. The users as well as the nodes
  credentials are managed through this service.


Recommended components
^^^^^^^^^^^^^^^^^^^

The following components are in principle optional, but recommended to use vantage6.

:ref:`User interface <hub-admin-guide-ui>`
  A web interface that allows your users to interact more easily with the vantage6 hub.

:ref:`Algorithm store <hub-admin-guide-store>`
  The algorithm store is used to store and manage algorithms for your project.
  Managing your algorithms in the store in the store is required if you want to use them
  in the UI. If your projects only uses algorithms that are available in the
  :ref:`community store <community-store>`, you don't need your own algorithm store.

:ref:`docker-registry`
  You can use the (public) `Docker hub <https://hub.docker.com/>`_ to upload your
  algorithm Docker images. However, for production scenarios, where you want to work
  with sensitive data, we recommend storing your own algorithms in your own Docker
  registry.

:ref:`Mailserver <smtp-server>`
  If you want to send emails to your users, e.g. to help them reset their
  password, you need to set up an SMTP server.

Optional components
^^^^^^^^^^^^^^^^^^^

:ref:`Message broker <hub-admin-guide-rabbitmq>`
  If you have an HQ with a high workload, you may want to set up a RabbitMQ message
  queue service to improve the performance. This enables horizontal scaling of the
  vantage6 HQ. Note that is easy to add this service to the hub as it can be
  deployed as part of the vantage6 HQ.

:ref:`Blob storage <azure-blob-storage>`
  In order to facilitate usage of large input arguments and output results for your
  algorithms, it is possible to use Azure Blob Storage for storage rather than the
  relational database.

:ref:`Prometheus <hub-admin-guide-prometheus>`
  If you want to monitor the performance of your vantage6 hub and nodes, you can use
  Prometheus. This is a powerful tool that allows you to monitor various metrics from
  your vantage6 hub and nodes.

Table of contents
^^^^^^^^^^^^^^^^^

.. toctree::
    :maxdepth: 3

    components/index
    services/index
    requirements
    install
    use
    deploy
