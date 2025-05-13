.. include:: <isonum.txt>

.. _technical-reference:

Technical reference
===================

This section contains technical reference information about the vantage6 project.


.. toctree::
    :maxdepth: 3

    architecture
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
