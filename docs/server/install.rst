.. _install-server:

Install
-------

Local (test) Installation
^^^^^^^^^^^^^^^^^^^^^^^^^

To install the **vantage6 server**, make sure you have met the
:ref:`requirements <server-requirements>`. Then, we provide a command-line
interface (CLI) with which you can manage your server. The CLI is a Python
package that can be installed using pip. We always recommend to install the CLI
in a `virtual environment <https://docs.python.org/3/tutorial/venv.html>`_ or
a `conda environment <https://docs.conda.io/projects/conda/en/latest/user-guide/concepts/environments.html>`_.

Run this command to install the CLI in your environment:

::

   pip install vantage6

Or if you want to install a specific version:

::

   pip install vantage6==x.y.z


You can verify that the CLI has been installed by running the command
``vserver --help``. If that prints a list of commands, the installation is
completed.

The server software itself will be downloaded when you start the server for the
first time.

Host your server
^^^^^^^^^^^^^^^^

To host your server, we recommend to use the Docker image we
provide: ``harbor2.vantage6.ai/infrastructure/server``. Running this
docker image will start the server. Check the
:ref:`server-deployment` section for deployment examples.

.. note::

    We recommend to use the latest version. Should you have reasons to
    deploy an older ``VERSION``, use the image
    ``harbor2.vantage6.ai/infrastructure/server:<VERSION>``.

    If you deploy an older version, it is also recommended that the nodes match
    that version. They can do that by specifying the ``--image`` flag in
    their configuration file (see :ref:`this section <node-configure-structure>`
    on node configuration).
