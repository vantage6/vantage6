Quickstart
==========

This quickstart section will show you how to run a vantage6 network, comprising of a
central server, three nodes, an algorithm store and a user interface, on your local
machine.

Requirements
------------

Make sure you have installed Docker and Python. These are required for all vantage6
components. Installation instructions are present, for instance, in the
:ref:`server requirements <server-requirements>` section.

Installation
------------

Create a virtual Python environment. We recommend installing
`Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_. If you are using
miniconda, you can create and activate a Python environment called 'vantage6_env' with:

.. code-block:: bash

    conda create -n vantage6_env python=3.13
    conda activate vantage6_env

Then, install the vantage6 command line interface (CLI) by running:

.. code-block:: bash

    pip install vantage6

.. _create-dev-network:

Start a local vantage6 network
------------------------------

Before starting a local vantage6 network, make sure Docker is running. Then, in the
Python environment where you installed the vantage6 CLI, you can easily set up a local
vantage6 network by running the following command:

.. code-block:: bash

    v6 dev create-demo-network

This will start an interactive dialog that will ask you to provide a name for the
network. Note that default settings are used - you can view custom options with
``v6 dev create-demo-network --help``.

.. note::

    If you are using Linux without Docker Desktop, you should set the default Docker
    host URL. You can do this by running
    ``v6 dev create-demo-network --server-url http://172.17.0.1``. By default, the
    host URL is assumed to be ``http://host.docker.internal`` (Docker desktop's default).

Next, you can start the network by running:

.. code-block:: bash

    v6 dev start-demo-network

Using the default settings, this will start up a server, three nodes, an algorithm store
and a user interface. The nodes contain some
`test data <https://github.com/vantage6/vantage6/blob/main/vantage6/vantage6/cli/dev/data/olympic_athletes_2016.csv>`_
about olympic medal winners. Note also that the server is coupled automatically to the
community algorithm store, thereby making the community algorithms directly available to
you.

You can now access the user interface by navigating to http://localhost:7600 in your
browser and log in with the username ``dev_admin`` and password ``password``. Enjoy!

Stopping the network
--------------------

Once you are done, you can stop and remove the network by running:

.. code-block:: bash

    # Stop the network
    v6 dev stop-demo-network

    # Remove the network permanently (clean up logs, configuration files, etc)
    v6 dev remove-demo-network