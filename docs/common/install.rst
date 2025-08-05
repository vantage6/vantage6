.. _install-server:

Install
-------

Local (test) Installation
^^^^^^^^^^^^^^^^^^^^^^^^^

To install the vantage6 |instance-type|, make sure you have met the
|requirements-link|. Then, we provide a command-line interface (CLI) with which
you can manage your |instance-type|. The CLI is a Python package that can be
installed using uv. We always recommend to install the CLI
in a `virtual environment <https://docs.python.org/3/tutorial/venv.html>`_,
for example using `uv <https://docs.astral.sh/uv/>`_.

Run this command to install the CLI in your environment:

::

   uv add vantage6

Or if you want to install a specific version:

::

   uv add vantage6==x.y.z


You can verify that the CLI has been installed by running the command
``v6 --help``. If that prints a list of commands, the installation is
completed.

The |instance-type| software itself will be downloaded when you start the
|instance-type| for the first time.

Hosting your |instance-type|
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To host your |instance-type|, we recommend to use the Docker image we
provide: |image|. Running this docker image will start the server. Check the
|deployment-link| section for deployment examples.

.. note::

    We recommend to use the latest version. Should you have reasons to
    deploy an older ``VERSION``, use the image |image-old|.