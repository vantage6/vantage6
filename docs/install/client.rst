.. _client install:

Client
------

We provide four ways in which you can interact with the server to manage
your vantage6 resources: the :ref:`install_ui` (UI), the
:ref:`Python client <python client library>`, the
:ref:`R client <r client library>`, and the server API. Below are installation
instructions for each of them.

For most use cases, we recommend to use the UI (for anything except
creating tasks - this is coming soon) and/or the Python Client. The latter
covers the server functionality completely, but is more convenient for most
users than sending HTTP requests directly to the API.

.. warning::
    Depending on your algorithm it *may* be required to use a specific
    language to post a task and retrieve the results. This could happen when
    the output of an algorithm contains a language specific datatype and or
    serialization.

.. _install_ui:

User interface
^^^^^^^^^^^^^^

The UI is available as a website, so you don't have to install anything! Just
go to the webpage and login with your user account. If you are using the
Petronas server, simply go to https://portal.petronas.vantage6.ai.

If you are a server admin and want to set up a user interface, see :ref:`UI`.

Python client library
^^^^^^^^^^^^^^^^^^^^^

Before you install the Python client, we check the version of the server you
are going to interact with first. If you are using an existing server, check
``https://<server_url>/version`` (e.g. `https://petronas.vantage6.ai/version`
or `http://localhost:5000/api/version`) to find its version.

Then you can install the ``vantage6-client`` with:

::

   pip install vantage6==<version>

where you add the version you want to install. You may also leave out
the version to install the most recent version.

.. _r client install:

R client library
^^^^^^^^^^^^^^^^

The R client currently only supports creating tasks and retrieving their
results. It can not (yet) be used to manage resources, such as creating
and deleting users and organizations.

You can install the R client by running:

.. code:: r

   devtools::install_github('IKNL/vtg', subdir='src')


Server API
^^^^^^^^^^

The API can be called via HTTP requests from a programming language of your
choice. Hence, what you need to install, depends on you!

You can explore how to use the server API on ``https://<serverdomain>/apidocs``
(e.g. https://petronas.vantage6.ai/apidocs for our Petronas server).
