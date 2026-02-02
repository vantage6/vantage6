.. include:: <isonum.txt>

.. _node-admin-guide:

Node admin guide
================

.. _node-intro:

The vantage6 node is the software that runs on the machine of the data
owner. It is responsible for the execution of the federated learning
tasks and the communication with vantage6 HQ.

Each organization that is involved in a federated learning collaboration has
its own node in that collaboration. They should therefore install the node
software on a virtual machine hosted in their own infrastructure. The node
should have access to the data that is used in the federated learning
collaboration.

The following pages explain how to install and run the node software.

.. toctree::
    :maxdepth: 3

    requirements
    install
    use
    configure
