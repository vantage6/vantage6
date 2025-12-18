.. _quickstart:

Quickstart
==========

This quickstart section will show you how to run a vantage6 network, comprising of
three nodes and a vantage6 hub (consisting of HQ, authentication service, algorithm
store and user interface), on your local machine.

Requirements
------------

Make sure you have installed Python and a form of Kubernetes. These are required for
all vantage6 components. Installation instructions are present, for instance, in the
:ref:`hub requirements <hub-requirements>` section.

If you are using Docker Desktop, you can simply
`switch on Kubernetes <https://docs.docker.com/desktop/features/kubernetes/>`_.
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

    uv pip install vantage6

.. TODO v5+ remove note below

.. note::

    While vantage6 5.0.0 has not yet been released, you can install the latest version of the CLI
    by running:

    .. code-block:: bash

        uv pip install vantage6 --prerelease=allow

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

The network is automatically started. Using the default settings, this will start up
all necessary components of the hub and three nodes. The nodes contain some
`test data <https://github.com/vantage6/vantage6/blob/main/vantage6/vantage6/cli/sandbox/data/olympic_athletes_2016.csv>`_
about olympic medal winners. Note also that HQ is coupled automatically to the
community algorithm store, thereby making the community algorithms directly available to
you in your local setup.

You can now access the user interface by navigating to http://localhost:30760 in your
browser and log in with the username ``admin`` and password ``admin``. Enjoy!

.. note::

    If you are using Windows or WSL with Docker Desktop to run your sandbox, the sandbox
    files are stored in a WSL folder. Unfortunately, this folder is deleted when you
    restart WSL or your machine itself. This means your sandbox will be lost.

    Also, note that to run the sandbox from WSL, you need to install ``wslview`` so that
    WSL can initiate the authentication process in your browser. To install it, run:

    .. code-block:: bash

        sudo apt-get install wslview

.. note::

    For those using Microk8s, we have seen networking issues when you move your machine
    to a different network, e.g. from home to work. What we found helped is to reset the
    certificates of your microk8s cluster, so that they no longer depend on an outdated
    IP address. To do this, run:

    .. code-block:: bash

        microk8s config > ~/.kube/config
        kubectl config use-context microk8s
        sudo microk8s refresh-certs --cert ca.crt

Stopping the network
--------------------

Once you are done, you can stop and remove the network by running:

.. code-block:: bash

    # Stop the network
    v6 sandbox stop

    # Remove the network permanently (clean up logs, configuration files, etc)
    v6 sandbox remove

Note that you can always run ``v6 sandbox start`` to start the network again.