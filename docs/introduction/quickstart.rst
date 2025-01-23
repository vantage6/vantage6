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

    conda create -n vantage6_env python=3.10
    conda activate vantage6_env

Then, install the vantage6 command line interface (CLI) by running:

.. code-block:: bash

    pip install vantage6

Start a local vantage6 network
------------------------------

You can easily set up a local vantage6 network by running the following command:

.. code-block:: bash

    v6 dev create-demo-network

This will start an interactive dialog that will help you to easily configure your server
and nodes. Note that you can also do ``v6 dev create-demo-network --help`` to view
which custom options are available.

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