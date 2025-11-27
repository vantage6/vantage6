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

   uv pip install vantage6

Or if you want to install a specific version:

::

   uv pip install vantage6==x.y.z


You can verify that the CLI has been installed by running the command
``v6 --help``. If that prints a list of commands, the installation is
completed.

The |instance-type| software itself will be downloaded when you start the
|instance-type| for the first time.

Hosting your |instance-type|
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To host your |instance-type|, we recommend to use the Helm chart we provide:
|chart-link|. Check the |deployment-link| section for deployment examples.

.. note::

    We recommend to use the latest version. Should you have reasons to
    deploy an older version use the helm chart. For instance, for version 5.0.0, use
    the chart |chart-5.0.0-link|.