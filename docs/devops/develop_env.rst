Development environment
=======================

This document describes the development environment for the vantage6 project. When
developing new features or fixing bugs, it helps a lot to have your code changes
immediately reflected in the running system, which is why we have a development
environment.

The development environment is a `devspace <https://www.devspace.sh/>`_ environment
that runs a local kubernetes environment with all the services that make up a vantage6
infrastructure running in containers.

Requirements
------------

You need to have the following installed:

  - `devspace <https://www.devspace.sh/docs/getting-started/installation>`_ - to run the
    development environment
  - `kubectl <https://kubernetes.io/docs/tasks/tools/#kubectl>`_ - to manage the
    kubernetes cluster. It usually comes with your kubernetes distribution. supported
    distributions for the development environment are `microk8s <https://microk8s.io/>`_,
    `minikube <https://minikube.sigs.k8s.io/>`_ and
    `Docker Desktop <https://docs.docker.com/desktop/>`_.

.. warning::

    If you are using WSL, it may not be possible to open a browser window to
    authenticate from the command line.

Finally, to run the development environment, you need to clone the
`vantage6 repository <https://github.com/vantage6/vantage6>`_ and navigate to the
main directory.

Configuring the development environment
----------------------------------

You can configure the development environment by running any ``devspace`` command. The
first command that you run will prompt you to enter a number of variables to configure
the development environment. For example, you can run the environment with:

.. code-block:: bash

    cd /path/to/vantage6/repository
    devspace run start-dev

Take particular note of setting up the following variables:

  - ``HOST_URI``: this is the ip address of your host machine. If you are using Docker
    k8s (which comes with Docker Desktop), this should be ``host.docker.internal``. If
    you are using Linux, this is usually ``172.17.0.1``. You can also find out the ip
    with ``hostname -I | awk '{print $1}'`` (Linux) or
    ``ip route | awk '/default/ {print $3}`` (Mac).
  - ``NUMBER_OF_NODES``: this is the number of nodes you want to create for the
    development environment. For some algorithms, you need to have at least 3 nodes.
  - ``NODE_TEST_DATABASE_NAME``: this is the name of the test database for the nodes.
    This is used to store the test data for the nodes. Enter a suitable CSV file name.

.. warning::

    If you are using WSL with Docker Desktop, note that you
    `need to set custom mount paths <https://dev.to/nsieg/use-k8s-hostpath-volumes-in-docker-desktop-on-wsl2-4dcl>`_
    for the file paths. Note also that these files may be deleted when you restart
    WSL or your machine itself.

Running the development environment
----------------------------------

Once you have configured the development environment, you can manage it with the
following commands:

.. list-table::
   :name: devspace-commands
   :widths: 33 67
   :header-rows: 1

   * - Command
     - Description
   * - ``devspace run start-dev``
     - Start the development environment
   * - ``devspace run stop-dev``
     - Stop the development environment. This removes the running Kubernetes resources
       but keeps the local data (e.g. tasks data, database data)
   * - ``devspace run purge``
     - Delete all running k8s resources and local data (e.g. tasks data, database data)
   * - ``devspace run rebuild``
     - Rebuild all infrastructure Docker images for this project

By default, ``devspace run rebuild`` will build all images. You can rebuild specific
images by passing the ``--server``, ``--node``, ``--store`` or ``--ui`` flag. For
example, if you want to rebuild only the server image, you can run:

.. code-block:: bash

    devspace run rebuild --server

Using the development environment
--------------------------------

Once the development environment is running, it will spin up the following services:

- User interface (http://localhost:7600)
- Server (http://localhost:7601/server)
- One or more nodes (as indicated by the ``NUMBER_OF_NODES`` variable)
- Algorithm store (http://localhost:7602)
- Authentication (Keycloak), including the admin interface (http://localhost:8080)
- PostgreSQL databases to support the server, store and keycloak services

The following user is created to authenticate with:

- Username: ``admin``
- Password: ``admin``

The first time you start the development environment, you will be asked if you want to
populate the server with some example data. This is useful to test the development
environment. This will create additional users and organizations. The users will have
the username ``user_1`` (for organization ``org_1``), ``user_2`` (for organization
``org_2``), etc., up to the number of nodes you have configured. Each user will have
the password ``Password123!``.

.. note::

    You can find the logs of the development environment in the `.devspace/logs`
    directory. We also recommend using `k9s <https://k9scli.io/>`_ to interact with
    the Kubernetes cluster.







