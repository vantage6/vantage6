Logging
=======

.. _algorithm-store-logging:

Store
-----

Logging is enabled by default. To configure the logger, look at the ``logging``
section in the example configuration in :ref:`algorithm-store-config-file-structure`.

Useful commands:

1. ``v6 algorithm-store files``: shows you where the log file is stored
2. ``v6 algorithm-store attach``: show live logs of a running store in your
   current console. This can also be achieved when starting the store
   with ``v6 algorithm-store start --attach``

.. _server-logging:

Server
------

Logging is enabled by default. To configure the logger, look at the ``logging``
section in the example configuration in :ref:`server-config-file-structure`.

Useful commands:

1. ``v6 server files``: shows you where the log file is stored
2. ``v6 server attach``: show live logs of a running server in your
   current console. This can also be achieved when starting the server
   with ``v6 server start --attach``
