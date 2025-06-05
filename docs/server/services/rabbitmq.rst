RabbitMQ
========

The RabbitMQ service is a service that allows you to send and receive messages.


.. _rabbitmq-install:

RabbitMQ
""""""""


RabbitMQ is an optional component that enables the server to handle more
requests at the same time. This is important if a server has a high workload.

There are several options to host your own RabbitMQ server. You can run
`RabbitMQ in Docker <https://hub.docker.com/_/rabbitmq>`__ or host
`RabbitMQ on
Azure <https://www.golinuxcloud.com/install-rabbitmq-on-azure/>`__. When
you have set up your RabbitMQ service, you can connect the server to it
by adding the following to the server configuration:

::

   rabbitmq_uri: amqp://<username>:<password>@<hostname>:5672/<vhost>

Be sure to create the user and vhost that you specify exist! Otherwise,
you can add them via the `RabbitMQ management
console <https://www.cloudamqp.com/blog/part3-rabbitmq-for-beginners_the-management-interface.html>`__.
