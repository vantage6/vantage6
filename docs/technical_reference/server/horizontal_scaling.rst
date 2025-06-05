Horizontal scaling
------------------

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

How to use
~~~~~~~~~~

If you use multiple server instances, you should always connect them to the same
RabbitMQ instance. You can achieve this by adding your RabbitMQ server when you
create a new server with :code:`v6 server new`, or you can add it later to your
server configuration file as follows:

.. code:: yaml

  rabbitmq_uri: amqp://$user:$password@$host:$port/$vhost

Where :code:`$user` is the username, :code:`$password` is the password,
:code:`$host` is the URL where your RabbitMQ service is running, :code:`$port` is
the queue's port (which is 5672 if you are using the RabbitMQ Docker image), and
:code:`$vhost` is the name of your
`virtual host <https://www.rabbitmq.com/vhosts.html>`_ (you could e.g. run one
instance group per vhost).

Deploy
++++++

If you are running a test server with ``v6 server start``, a RabbitMQ docker
container will be started automatically for you. This docker container contains
a management interface which will be available on port 15672.

For deploying a production server, there are several options to run RabbitMQ.
For instance, you can install `RabbitMQ on Azure <https://www.golinuxcloud.com/install-rabbitmq-on-azure>`_.