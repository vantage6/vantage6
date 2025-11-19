.. include:: <isonum.txt>

.. _server-admin-guide-ui:

UI
==

This section describes the UI component of the vantage6 server.


.. _install-ui:

User Interface
""""""""""""""

The User Interface (UI) is a web application that makes it easier for your
users to interact with the server. The UI is deployed together with the server, since it
is tightly coupled to the server.
The Kubernetes services that deploy the UI are part of the server Helm chart. Hence,
you merely need to start the server and the UI will be started automatically.
