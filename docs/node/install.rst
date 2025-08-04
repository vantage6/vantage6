
.. _install-node:

Install
-------

To install the **vantage6 node** make sure you have met the
:ref:`requirements <node-requirements>`. Then, we provide a command-line
interface (CLI) with which you can manage your node. The CLI is a Python
package that can be installed using uv. We always recommend to install the CLI
in a `virtual environment <https://docs.python.org/3/tutorial/venv.html>`_.

Run this command to install the CLI in your environment:

::

   # using uv (recommended)
   uv add vantage6

   # or, if you are using conda / pyenv / ...
   pip install vantage6

Or if you want to install a specific version:

::

   uv add vantage6==x.y.z

   # or, if you are using conda / pyenv / ...
   pip install vantage6==x.y.z

You can verify that the CLI has been installed by running the command
``v6 node --help``. If that prints a list of commands, the installation is
completed.

The next pages will explain to configure, start and stop the node. The
node software itself will be downloaded when you start the node for the first
time.

