.. _client install:

Client
======

We provide four ways in which you can interact with the server to manage
your vantage6 resources: the user interface (UI), the Python client, the
R client, and the server API.

What you need to install depends on which interface you choose. In order
to use the UI or the server API, you usually don’t need to install
anything: the UI is a website, and the API can be called via HTTP
requests from a programming language of your choice. For the UI, you
only need to set it up in case you are setting up your own server (see
:ref:`UI` for instructions).

Installation instructions for the Python client and R client are below.
For most use cases, we recommend to use the UI (for anything except
creating tasks) and/or the Python Client (which covers server API
functionality completely).

Python client library
^^^^^^^^^^^^^^^^^^^^^

Before you install the Python client, we recommended to check the
version of the server you are going to interact with first. The easiest
way of doing that is checking the ``/version`` endpoint of the server
you are going to use on ``https://<server_url>/version`` (e.g.
`https://petronas.vantage6.ai/version` or `http://localhost:5000/api/version`).

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
