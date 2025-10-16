.. include:: <isonum.txt>

.. _server-admin-guide:

Server admin guide
==================

Required components
^^^^^^^^^^^^^^^^^^^

:ref:`install-server`
  The vantage6 server is the core component of the vantage6 infrastructure.
  It is responsible for managing the nodes and tasks.

:ref:`install-auth`
  Vantage6 authentication is managed through a separate
  `Keycloak <https://www.keycloak.org/>`_ service. The users as well as the nodes
  credentials are managed through this service.


Optional components
^^^^^^^^^^^^^^^^^^^

There are several optional components that you can set up apart from the
vantage6 server itself. While they are not required, they usually make it much easier to
use vantage6.

:ref:`User interface <server-admin-guide-ui>`
  A web interface that allows your users to interact more easily the vantage6 server.

:ref:`Algorithm store <server-admin-guide-store>`
  The algorithm store is used to store and manage algorithms for your project.
  Managing your algorithms in the store in the store is required if you want to use them
  in the UI. If your projects only uses algorithms that are available in the
  :ref:`community store <community-store>`, you don't need your own algorithm store.

:ref:`docker-registry`
  You can use the (public) `Docker hub <https://hub.docker.com/>`_ to upload your
  algorithm Docker images. However, for production scenarios, where you want to work
  with sensitive data, we recommend storing your own algorithms in your own Docker
  registry.

:ref:`Message broker <rabbitmq-install>`
  If you have a server with a high workload, you may want to set up a RabbitMQ message
  queue service to improve the performance. This enables horizontal scaling of the
  vantage6 server.

:ref:`Mailserver <smtp-server>`
  If you want to send emails to your users, e.g. to help them reset their
  password, you need to set up an SMTP server.

:ref:`azure-blob-storage <azure-blob-storage>`
  In order to facilitate usage of large inputs and results for your algorithms,
  it is possible to use Azure Blob Storage for storage rather than the relational
  database.

The table of contents below lists details on how to install, configure and deploy these
components.

.. toctree::
    :maxdepth: 3

    requirements
    components/index
    services/index
    cli
    deploy
    logging
