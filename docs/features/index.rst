.. _feature-docs:

Feature descriptions
====================

**Under construction**

The vantage6 platform contains many features - some of which are optional, some
which are always active. This section aims to give an overview of the features
and how they may be used.

Each component has its own set of features. The features are described in the
following sections, as well as a section on inter-component features.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   server/index
   node/index
   algorithms/index
   inter-component/index

.. todo add the following features. Not sure if they all go here, or in the
   component specific sections.
.. - how node authentication works
.. - VPN: extend how to use it in an algorithm, extend tech docs how to debug it (n2n algorithm)
.. - Algorithm environment variables
.. - algorithm wrappers
..    - how calling algorithm function works in there (dispatch)
.. - gpu support (nodes)
.. - task flow
.. - task encryption
.. - task serialization/deserialization (maybe just for developers?)
.. - policies node
.. - use private docker registry (node)
.. - logging settings
.. - sharing node configuration with server
.. - settings on validity of JWT tokens (server admin)
.. - node proxy server
.. - killing algorithms remotely
.. - socket stuff - users/nodes can connect to server via socket - now only nodes described I think
.. - Permission system
..    - default roles
.. - user interface (?) - how to use it
.. - mail service
.. - Full documentation of the CLI - may need to extend 'use' section of the guides
.. - RabbitMQ
.. - The different types of clients - userClient, nodeClient, AlgorithmClient
..     - their general structure
.. - MockClient
.. -
.. -

.. for developers:
.. - how to run unit tests
.. - how to use a different image for node/server for development purposes
.. - Server API - general description
.. - Database model
.. - How configuration is managed
.. -

