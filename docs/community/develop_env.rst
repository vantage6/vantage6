.. _develop-env:

Development environment
=======================

This document describes the development environment for the vantage6 project. When
developing new features or fixing bugs, it helps a lot to have your code changes
immediately reflected in the running system, which is why we have a development
environment.

The development environment is a `devspace <https://www.devspace.sh/>`_ environment
that runs a local kubernetes environment with all the services that make up a vantage6
infrastructure running in containers.

.. warning::

    If you are using Windows, you need to have the
    `Windows Subsystem for Linux <https://learn.microsoft.com/en-us/windows/wsl/install>`_
    (WSL) installed, and call the development environment from within WSL. The
    development environment is not supported on Windows itself.

Requirements
------------

You need to have the following installed:

- A Python 3.13 virtual environment with vantage6 installed in development mode, as
  described in :ref:`submit-patch`. Activate it before running any of the commands
  below since ``v6 dev`` commands come from it, and the development environment runs
  helper scripts with that Python.
- `Docker <https://docs.docker.com/engine/install/>`_ - to build the infrastructure images
- `devspace <https://www.devspace.sh/docs/getting-started/installation>`__ (tested with
  version 6.3) - to run the development environment. Devspace downloads its own copy of Helm,
  so you don't need to install Helm separately.
- `kubectl <https://kubernetes.io/docs/tasks/tools/#kubectl>`_ - to manage the kubernetes cluster.
  It usually comes with your kubernetes distribution. Supported distributions for the development
  environment are `microk8s <https://microk8s.io/>`_,
  `minikube <https://minikube.sigs.k8s.io/>`_ and
  `Docker Desktop <https://docs.docker.com/desktop/>`_.

.. warning::

    If you are using WSL, it may not be possible to open a browser window to
    authenticate from the command line. There are multiple ways to fix this.
    `This StackOverflow question <https://superuser.com/questions/1262977/open-browser-in-host-system-from-windows-subsystem-for-linux>`_
    has some solutions.

Finally, to run the development environment, you need to clone the
`vantage6 repository <https://github.com/vantage6/vantage6>`_ and navigate to the
main directory.

Preparing the kubernetes cluster
--------------------------------

The databases, logs and task data of the development environment are stored on your machine through hostPath volumes. 
By default they are stored in the ``dev`` folder of the repository. 
Your cluster must be able to see that folder at the same path.

minikube
^^^^^^^^

With the docker driver, minikube runs inside a container, so you need to mount the ``dev`` folder into it. 
Run this from the root of the repository:

.. code-block:: bash

    minikube start --driver=docker --cpus=8 --memory=16g \
      --mount --mount-string="$PWD/dev:$PWD/dev"

The mount can only be set when the cluster is created.
If you already have a minikube cluster, remove it first with ``minikube delete``.

.. note::

    minikube's default network plugin does not enforce Kubernetes NetworkPolicies. As
    a result, the nodes log the warning ``Algorithm network isolation check failed``.
    This is harmless in the development environment.

microk8s
^^^^^^^^

Enable the hostpath storage addon:

.. code-block:: bash

    microk8s enable hostpath-storage

Docker Desktop
^^^^^^^^^^^^^^

Enable Kubernetes in the Docker Desktop settings. 
On WSL, see the warning in :ref:`develop-env-first-run` about custom mount paths.

.. _develop-env-first-run:

First time running the development environment
----------------------------------------------

To run the development environment for the first time, execute these commands:

.. code-block:: bash

    cd /path/to/vantage6/repository

    # Recommended: use a separate namespace instead of the default kubernetes namespace.
    kubectl create namespace vantage6
    kubectl config set-context --current --namespace=vantage6

    # Build the infrastructure images from your local code
    v6 dev rebuild

    # Start the development environment
    v6 dev start

The first command that uses devspace (here: ``v6 dev rebuild``) asks you a number of questions to configure
the development environment. Your answers are saved in ``.devspace/cache.yaml``.
To change them later, run ``devspace reset vars`` and you will be asked again.

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Variable
     - What to enter
   * - ``K8S_NODE_NAME``
     - The name of your kubernetes node, as shown by ``kubectl get nodes``.
       This is ``docker-desktop`` for Docker Desktop and ``minikube`` for minikube.
       For microk8s, it is usually the hostname of your machine.
   * - ``NUMBER_OF_NODES``
     - The number of vantage6 nodes to create.
       For some algorithms, you need at least 3 nodes.
   * - ``NODE_TEST_DATABASE_NAME``
     - The name of the CSV file that the nodes use as test database.
       The default ships with the repository.
   * - ``HOST_URI``
     - Only used as the default answer for ``PORTS_BIND_ADDRESS``. Any value works.
   * - ``PORTS_BIND_ADDRESS``
     - The address on which the services are exposed on your machine.
       Use ``localhost``; if the services should be reachable from other machines use ``0.0.0.0`` instead.
   * - ``NODE_TEST_DATABASE_MOUNT_PATH``
     - The folder that contains the test database. Keep the default unless you use WSL.
   * - ``HOST_DATA_PATH``
     - The folder where databases, logs and task data are stored. Keep the default unless you use WSL.

``v6 dev rebuild`` builds the images directly into your cluster. If you skip it, the images are pulled from our registry instead, and these may be outdated.

``v6 dev start`` then does the following:

1. It installs the Keycloak operator in your cluster, if it is not there yet.
2. It deploys the authentication service, the algorithm store and HQ.
3. It populates the hub with example data (see :ref:`develop-env-using`).
   To do so, it logs in to HQ: a browser window opens where you log in with
   the default credentials; username: ``admin`` and password: ``admin``.
   If no browser opens, follow the link printed in the terminal.
4. It deploys the nodes.

The command keeps running in the foreground to sync your code changes into the containers, it will take a while.
Press ``Ctrl+C`` to stop it.

.. warning::

    If you are using WSL with Docker Desktop, note that you
    `need to set custom mount paths <https://dev.to/nsieg/use-k8s-hostpath-volumes-in-docker-desktop-on-wsl2-4dcl>`_
    for the file paths. Note also that these files may be deleted when you restart
    WSL or your machine itself.

.. note::

    Because the mount path is located outside of the repository on WSL, the test datasets
    that are shipped in the ``dev`` folder are copied to ``NODE_TEST_DATABASE_MOUNT_PATH``
    automatically every time you start the development environment. This also restores them
    after a WSL restart. If a dataset with the same name is already present at that
    location, it is left untouched, so you can safely put your own test data there.

Running the development environment
-----------------------------------

Once you have configured the development environment, you can manage it with the
following commands:

.. list-table::
   :name: devspace-commands
   :widths: 33 67
   :header-rows: 1

   * - Command
     - Description
   * - ``v6 dev start``
     - Start the development environment
   * - ``v6 dev stop``
     - Stop the development environment. This removes the running Kubernetes resources
       but keeps the local data (e.g. tasks data, database data)
   * - ``v6 dev clean``
     - Delete all running k8s resources and local data (e.g. tasks data, database data).
       On Linux, this asks for your ``sudo`` password, because the database files are owned by the database containers.
   * - ``v6 dev rebuild``
     - Rebuild all infrastructure Docker images (HQ, node, etc.)

By default, ``v6 dev rebuild`` will build all images.
You can rebuild a specific image by passing the ``--only-hq``, ``--only-node``, ``--only-store`` or ``--only-ui`` flag. 
For example, if you want to rebuild only the HQ image, you can run:

.. code-block:: bash

    v6 dev rebuild --only-hq

By default, ``v6 dev start`` populates the hub with example data the first time it runs, and after ``v6 dev clean``.
You can change this with these options:

- ``--no-populate``: don't populate the hub. The nodes get their configuration from populating (stored in ``dev/.data``), so without it they won't be able to connect.
- ``--repopulate``: delete all data and populate the hub again.
- ``--no-local-auth``: use an external Keycloak instead of a local one. Set its details in ``.devspace/.env``.

.. _develop-env-using:

Using the development environment
---------------------------------

Once the development environment is running, it will spin up the following services:

- The vantage6 hub, consisting of:

  - User interface (http://localhost:7600)
  - HQ (http://localhost:7601/hq)
  - Algorithm store (http://localhost:7602/store)
  - Authentication (Keycloak), including the admin interface (http://localhost:7680)
  - PostgreSQL databases to support the HQ, store and authentication services. 
    The HQ and store databases are available on ports 7632 and 7633.

- One or more nodes (as indicated by the ``NUMBER_OF_NODES`` variable)

The following user is created to authenticate with:

- Username: ``admin``
- Password: ``admin``

The example data adds organizations and users.
The users have the username ``user_1`` (for organization ``org_1``), ``user_2`` (for organization ``org_2``), etc., up to the
number of nodes you have configured.
Each user has the password ``Password123!``.
When you log in as one of these users for the first time, you are asked to fill in an email address and name.

Changes to the Python code of HQ, the algorithm store and the nodes, and to the UI code, are synced into the running containers, which then reload automatically.

.. note::

    Starting the development environment updates the ``Chart.lock`` files in the ``charts`` folder.
    Don't commit these changes.

.. note::

    You can find the logs of the development environment in the `.devspace/logs`
    directory. We also recommend using `k9s <https://k9scli.io/>`_ to interact with
    the Kubernetes cluster.
