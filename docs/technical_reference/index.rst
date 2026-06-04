.. include:: <isonum.txt>

.. _technical-reference:

Technical reference
===================

This section contains technical reference information about the vantage6 project.


.. toctree::
    :maxdepth: 3

    architecture
    hub/index
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
.. - logging settings
.. - sharing node configuration with HQ
.. - settings on validity of JWT tokens (HQ admin)
.. - node proxy
.. - killing algorithms remotely
.. - socket stuff - users/nodes can connect to HQ via socket - now only nodes described I think
.. - Permission system
..    - default roles
.. - mail service
.. - Full documentation of the CLI - may need to extend 'use' section of the guides
.. - The different types of clients - userClient, nodeClient, AlgorithmClient
..     - their general structure
.. - MockClient
.. -
.. -

.. for developers:
.. - how to run unit tests
.. - HQ API - general description
.. - Database model
.. - How configuration is managed
.. -
