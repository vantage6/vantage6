Quickstart
==========

This quickstart section will show you how to run a vantage6 network, comprising of a
central server, three nodes, an algorithm store and a user interface, on your local
machine.

Requirements
------------

Make sure you have installed Python and a form of Kubernetes. These are required for
all vantage6 components. Installation instructions are present, for instance, in the
:ref:`server requirements <server-requirements>` section.

If you are using Docker Desktop, you can simply
:ref:`switch on Kubernetes <https://docs.docker.com/desktop/features/kubernetes/>`_.
Otherwise, we recommend installing `microk8s <https://microk8s.io/>`_.

Installation
------------

Create a virtual Python environment. We recommend using
`uv <https://docs.astral.sh/uv/>`_ for package management. You can create and activate
a Python environment with:

.. code-block:: bash

    uv venv --python 3.13
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate

Then, install the vantage6 command line interface (CLI) by running:

.. code-block:: bash

    uv add vantage6

.. _create-dev-network:

Start a local vantage6 network
------------------------------

In the Python environment where you installed the vantage6 CLI, you can easily set up a
local vantage6 network by running the following command:

.. code-block:: bash

    v6 sandbox new

This will start an interactive dialog that will ask you to provide a name for the
network. Note that default settings are used - you can view custom options with
``v6 sandbox new --help``.

The network is automatically started. Using the default settings, this will start up a
server, three nodes, an algorithm store and a user interface. The nodes contain some
`test data <https://github.com/vantage6/vantage6/blob/main/vantage6/vantage6/cli/sandbox/data/olympic_athletes_2016.csv>`_
about olympic medal winners. Note also that the server is coupled automatically to the
community algorithm store, thereby making the community algorithms directly available to
you.

You can now access the user interface by navigating to http://localhost:7600 in your
browser and log in with the username ``admin`` and password ``admin``. Enjoy!

Stopping the network
--------------------

Once you are done, you can stop and remove the network by running:

.. code-block:: bash

    # Stop the network
    v6 sandbox stop

    # Remove the network permanently (clean up logs, configuration files, etc)
    v6 sandbox remove

Note that you can always run ``v6 sandbox start`` to start the network again.