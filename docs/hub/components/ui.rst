.. include:: <isonum.txt>

.. _hub-admin-guide-ui:

UI
==

This section describes the UI component of the vantage6 hub.

.. _install-ui:

User Interface
""""""""""""""

The User Interface (UI) is a web application that makes it easier for your
users to interact with the vantage6 hub. The UI is deployed together with HQ, since it
is tightly coupled to it.
The Kubernetes services that deploy the UI are part of the HQ Helm chart. Hence,
you merely need to start HQ and the UI will be started automatically.
