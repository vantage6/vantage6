Message broker
========

The RabbitMQ message broker is important if your server has a high workload.

It is required to enable horizontal scaling of the server.
By horizontal scaling, we mean that you can run multiple instances of the
vantage6 server simultaneously to handle a high workload. This is useful when a
single machine running the server is no longer sufficient to handle all
requests.

How it works
~~~~~~~~~~~~

Horizontal scaling with vantage6 can be done using a
`RabbitMQ server <https://https://www.rabbitmq.com/>`_. RabbitMQ is a widely
used message broker. Below, we will first explain how we use RabbitMQ, and
then discuss the implementation.

The websocket connection between server and nodes is used to process various
changes in the network's state. For example, a node can create a new (sub)task
for the other nodes in the collaboration. The server then communicates these
tasks via the socket connection. Now, if we use multiple instances of the
central server, different nodes in the same collaboration may connect to
different instances, and then, the server would not be able to deliver the new
task properly. This is where RabbitMQ comes in.

When RabbitMQ is enabled, the websocket messages are directed over the RabbitMQ
message queue, and delivered to the nodes regardless of which server instance
they are connected to. The RabbitMQ service thus helps to ensure that all
websocket events are still communicated properly to all involved parties.

Deploy
++++++

.. TODO v5+ I guess this should be updated to how it works in k8s
There are several options for deploying a RabbitMQ server.
For instance, you can install `RabbitMQ on Azure <https://www.golinuxcloud.com/install-rabbitmq-on-azure>`_,
or use `RabbitMQ in Docker <https://hub.docker.com/_/rabbitmq>`__. When
you have set up your RabbitMQ service, you can connect the server to it
by adding the following to the server configuration:

::

   rabbitmq_uri: amqp://<username>:<password>@<hostname>:5672/<vhost>

Be sure to create the user and vhost that you specify exist! Otherwise,
you can add them via the `RabbitMQ management
console <https://www.cloudamqp.com/blog/part3-rabbitmq-for-beginners_the-management-interface.html>`__.

.. TODO v5+ check if the stuff below is still valid
.. note::

   If you are running a test server with ``v6 server start``, a RabbitMQ docker
   container will be started automatically for you. This docker container contains
   a management interface which will be available on port 15672.

How to use
~~~~~~~~~~

If you use multiple server instances, you should always connect them to the same
RabbitMQ instance. If you don't enter your RabbitMQ address during setup using
:code:`v6 server new`, you can add it later to your server configuration file as
follows:

.. code:: yaml

  rabbitmq_uri: amqp://$user:$password@$host:$port/$vhost

Where :code:`$user` is the username, :code:`$password` is the password,
:code:`$host` is the URL where your RabbitMQ service is running, :code:`$port` is
the queue's port (which is 5672 if you are using the RabbitMQ Docker image), and
:code:`$vhost` is the name of your `virtual host <https://www.rabbitmq.com/vhosts.html>`_.

