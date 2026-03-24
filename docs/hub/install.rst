
.. _install-hub:

Install
-------

Local installation
^^^^^^^^^^^^^^^^^^

To install the vantage6 hub, make sure you have met the
:ref:`requirements <hub-requirements>`. Then, we provide a command-line interface (CLI)
with which you can manage your hub. The CLI is a Python package that can be
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

Production installation
^^^^^^^^^^^^^^^^^^^^^^^

Check the :ref:`deployment <hub-deployment>` section for deployment examples.
