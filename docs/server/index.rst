.. include:: <isonum.txt>

.. _server-admin-guide:

Server admin guide
==================

Install optional components
^^^^^^^^^^^^^^^^^^^^^^^^^^^

There are several optional components that you can set up apart from the
vantage6 server itself.

:ref:`install-ui`
  An application that will allow your server's users to interact more easily
  with your vantage6 server.

:ref:`docker-registry`
  A (private) Docker registry can be used to store algorithms but it is also
  possible to use the (public) `Docker hub <https://hub.docker.com/>`__ to
  upload your Docker images. For production scenarios, we recommend using a
  private registry.

:ref:`eduvpn-install`
  If you want to enable algorithm containers that are running on different
  nodes, to directly communicate with one another, you require an eduVPN server
  version 3.

:ref:`rabbitmq-install`
  If you have a server with a high workload whose performance you want to
  improve, you may want to set up a RabbitMQ service which enables horizontal
  scaling of the Vantage6 server.


:ref:`smtp-server`
  If you want to send emails to your users, e.g. to help them reset their
  password, you need to set up an SMTP server.

Below, we explain how to install and deploy these components.

.. toctree::
    :maxdepth: 3

    introduction
    requirements
    components/index
    services/index
    cli
    deploy
    logging

    .. install
    .. optional
    .. use
    .. configure
    .. permissions