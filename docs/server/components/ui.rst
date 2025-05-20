.. include:: <isonum.txt>

.. _server-admin-guide-ui:

UI
==

This section describes the UI component of the vantage6 server.


.. _install-ui:

User Interface
""""""""""""""

The User Interface (UI) is a web application that will make it easier for your
users to interact with the server. It allows you to manage all your resources
(such as creating collaborations, editing users, or viewing tasks),
except for creating new tasks. We aim to incorporate this functionality
in the near future.

To run the UI, we also provide a Docker image. Below is an example of how you may
deploy a UI using Docker compose; obviously, you may need to adjust the configuration
to your own environment.

.. code:: yaml

    name: run-ui
    services:
      ui:
        image: harbor2.vantage6.ai/infrastructure/ui:cotopaxi
        ports:
          - "8000:80"
        environment:
          - SERVER_URL=https://<url_to_my_server>
          - API_PATH=/api

Alternatively, you can also run the UI locally with Angular. In that case, follow the
instructions on the `UI Github page <https://github.com/vantage6/vantage6/tree/main/vantage6-ui>`__

.. figure:: /images/screenshot_ui.jpg
    :alt: UI screenshot
    :align: center

    Screenshot of the vantage6 UI
