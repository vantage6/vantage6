Message broker
========

The `RabbitMQ message broker <https://https://www.rabbitmq.com/>`_ is important if your
server has a high workload.

It is required to enable horizontal scaling of the server.
By horizontal scaling, we mean that you can run multiple instances of the
vantage6 server simultaneously to handle a high workload. This is useful when a
single machine running the server is no longer sufficient to handle all
requests.

Below, we will first explain how RabbitMQ is used within vantage6, and then discuss how
you can deploy it.

How it works
~~~~~~~~~~~~

In vantage6, a websocket connection between server and nodes is used to process various
changes in the network's state. For example, a node can create a new (sub)task
for the other nodes in the collaboration. The server then communicates these
tasks via the socket connection. Now, if we use multiple instances of the
central server, different nodes in the same collaboration may connect to
different instances, and then, the server would not be able to deliver the new
task properly. This is where RabbitMQ comes in.

When RabbitMQ is enabled, the websocket messages are directed via the RabbitMQ
message queue, and delivered to the nodes regardless of which server instance
they are connected to. The RabbitMQ service thus helps to ensure that all
websocket events are still communicated properly to all involved parties.

Deploy
++++++

Deployment of RabbitMQ is straightforward: you merely need to start your vantage6 server
and RabbitMQ will be started automatically, as it is part of the server Helm chart.

You can configure your RabbitMQ instance by editing the RabbitMQ section of the
:ref:`server configuration file <server-configuration-file>`.