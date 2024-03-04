.. _server-intro:

Introduction
------------

The vantage6 server is the central component of the vantage6 platform. It is
responsible for managing the different organizations and their nodes,
authenticating and authorizing the users and nodes, and managing the
communication of task requests and results between the nodes and the users.

All communication in vantage6 is managed through the server's RESTful API and
socketIO server. There are also a couple of other services that you may want to
run alongside the server, such as a user interface and a message broker.

The following pages explain how to install and configure the server, and how to
run a test server or deploy a production server. It also explains which optional
services you may want to run alongside the server, and how to configure them.
