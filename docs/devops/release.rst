Release
=======

This page is intended to provide information about our release process. First,
we discuss the version formatting, after which we discuss the actual creation
and distribution of a release.

.. _format:

Version format
--------------
`Semantic versioning <https://semver.org/>`_ is used:
``Major.Minor.Patch.Pre[N].Post<n>``.

**Major** releases update the first digit, e.g. ``1.2.3`` is updated to
``2.0.0``. This is used for releasing breaking changes: server and nodes of
version 2.x.y are unlikely to be able to run an algorithm written for version
1.x.y. Also, the responses of the central server API may change in a way that
changes the response to client requests.

**Minor** releases update the second digit, e.g. ``1.2.3`` to ``1.3.0``. This is
used for releasing new features (e.g. a new endpoint), enhancements and other
changes that are compatible with all other components. Algorithms written for
version``1.x.y`` should run on any server of version ``1.z.a``. Also, the
central server API should be compatible with other minor versions - the same
fields present before will be present in the new version, although new fields
may be added. However, nodes and servers of different minor versions may not be
able to communicate properly.

**Patch** releases update the third digit, e.g. ``1.2.3`` to ``1.2.4``. This is
used for bugfixes and other minor changes. Different patch releases should be
compatible with each other, so a node of version ``1.2.3`` should be able to
communicate with a server of version ``1.2.4``.

**Pre[N]** is used for alpha (a), beta (b) and release candidates (rc) releases
and the build number is appended (e.g. ``2.0.1b1`` indicates the first
beta-build of version ``2.0.1``). These releases are used for testing before
the actual release is made.

**Post[N]** is used for a rebuild where no code changes have been made, but
where, for example, a dependency has been updated and a rebuild is required.
In vantage6, this is only used to version the Docker images that are updated
in these cases.

Testing a release
-------------------

Before a release is made, it is tested by the development team. They go through
the following steps to test a release:

1. *Create a release candidate*. This process is the same as creating
   the :ref:`actual release <create-release>`, except that the candidate has
   a 'pre' tag (e.g. ``1.2.3rc1`` for release candidate number 1 of version
   1.2.3). Note that for an RC release, no notifications are sent to Discord.
2. *Install the release*. The release should be tested from a clean conda
   environment.

  .. code:: bash

    conda create -n <name> python=3.10
    conda activate <name>
    pip install vantage6==<version>

3. *Start server and node*. Start the server and node for the release candidate:

  .. code:: bash

    v6 server start --name <server name>
        --image harbor2.vantage6.ai/infrastructure/server:<version>
        --attach
    v6 node start --name <node name>
        --image harbor2.vantage6.ai/infrastructure/node:<version>
        --attach

4. *Test code changes*. Go through all issues that are part of the new release
   and test their functionality.

5. *Run test algorithms*. The algorithm `v6-feature-tester` is run and checked.
   This algorithm checks several features to see if they are performing as
   expected. Additionaly, the `v6-node-to-node-diagnostics` algorithm is run
   to check the VPN functionality.

6. *Check swagger*. Check if the swagger docs run without error. They should be
   on http://localhost:5000/apidocs/ when running server locally.

7. *Test the UI*. Also make a release candidate there.

After these steps, the release is ready. It is executed for both the main
infrastructure and the UI. The release process is described below.

.. note::

  We are working on further automating the testing and release process.


.. _create-release:

Create a release
----------------
To create a new release, one should go through the following steps:

* Check out the correct branch of the `vantage6 <https://github.com/vantage6/vantage6>`_ repository and pull the latest version:

  ::

    git checkout main
    git pull

  *Make sure the branch is up-to-date*. **Patches** are usually directly
  merged into main, but for **minor** or **major** releases you usually need
  to execute a pull request from a development branch.

* Create a tag for the release. See :ref:`format` for more details on version names:

  ::

    git tag version/x.y.z

* Push the tag to the remote. This will trigger the release pipeline on Github:

  ::

    git push origin version/x.y.z

.. note::

    The release process is protected and can only be executed by certain
    people. Reach out if you have any questions regarding this.

The release pipeline
--------------------
The release pipeline executes the following steps:

1. It checks if the tag contains a valid version specification. If it does not,
   the process it stopped.
2. Update the version in the repository code to the version specified in the
   tag and commit this back to the main branch.
3. Install the dependencies and build the Python package.
4. Upload the package to PyPi.
5. Build and push the Docker image to `harbor2.vantage6.ai
   <https://harbor2.vantage6.ai>`_.
6. Post a message in Discord to alert the community of the new release. This
   is not done if the version is a pre-release (e.g. version/x.y.0rc1).

.. note::

    If you specify a tag with a version that already exists, the build pipeline
    will fail as the upload to PyPi is rejected.

The release pipeline uses a number of environment variables to, for instance,
authenticate to PyPi and Discord. These variables are listed and explained
in the table below.

.. list-table:: Environment variables
   :header-rows: 1
   :widths: 30 70

   * - Secret
     - Description
   * - ``COMMIT_PAT``
     - Github Personal Access Token with commit privileges. This is linked to
       an individual user with admin right as the commit on the ``main`` needs
       to bypass the protections. There is unfortunately not -yet- a good
       solution for this.
   * - ``ADD_TO_PROJECT_PAT``
     - Github Personal Access Token with project management privileges. This
       token is used to add new issues to project boards.
   * - ``COVERALLS_TOKEN``
     - Token from coveralls to post the test coverage stats.
   * - ``DOCKER_TOKEN``
     - Token used together ``DOCKER_USERNAME`` to upload the container images
       to our `<https://harbor2.vantage6.ai>`_.
   * - ``DOCKER_USERNAME``
     - See ``DOCKER_TOKEN``.
   * - ``PYPI_TOKEN``
     - Token used to upload the Python packages to PyPi.
   * - ``DISCORD_RELEASE_TOKEN``
     - Token to post a message to the Discord community when a new release is
       published.

.. _release-strategy:

Distribute release
------------------
Nodes and servers that are already running will automatically be upgraded to
the latest version of their major release when they are restarted. This
happens by pulling the newly released docker image. Note that the major
release is never automatically updated: for example, a node running version
2.1.0 will update to 2.1.1 or 2.2.0, but never to 3.0.0. Depending on the
version of vantage6 that is being used, there is a reserved Docker image tag
for distributing the upgrades. These are the following:

+---------------+------------------------+
| Tag           | Description            |
+===============+========================+
| cotopaxi      | ``4.x.x`` release      |
+---------------+------------------------+
| petronas      | ``3.x.x`` release      |
+---------------+------------------------+
| harukas       | ``2.x.x`` release      |
+---------------+------------------------+
| troltunga     | ``1.x.x`` release      |
+---------------+------------------------+

Docker images can be pulled manually with e.g.

::

  docker pull harbor2.vantage6.ai/infrastructure/server:cotopaxi
  docker pull harbor2.vantage6.ai/infrastructure/node:3.1.0

User Interface release
----------------------
The release process for the user interface (UI) is very similar to the release
of the infrastructure detailed above. The same versioning format is used, and
when you push a version tag, the automated release process is triggered.

We have semi-synchronized the version of the UI with that of the infrastructure.
That is, we try to release major and minor versions at the same time. For
example, if we are currently at version 3.5 and release version 3.6, we release
it both for the infrastructure and for the UI. However, there may be different
patch versions for both: the latest version for the infrastructure may then be
3.6.2 while the UI may still be at 3.6.

The release pipeline for the UI executes the following steps:

1. Version tag is verified (same as infrastructure).
2. Version is updated in the code (same as infrastructure).
3. Application is built.
4. Docker images are built and released to harbor2.
5. Application is pushed to our UI deployment slot (an Azure app service).


Post-release checks
-------------------

After a release, there are a few checks that are performed. Most of these are
only relevant if you are hosting a server yourself that is being automatically
updated upon new releases, as is for instance the case for the Cotopaxi server.

For Cotopaxi, the following checks are done:

- Check that harbor2.vantage6.ai has updated images ``server:cotopaxi``,
  ``server:cotopaxi-live`` and ``node:cotopaxi``.
- Check if the (live) server version is updated. Go to:
  https://cotopaxi.vantage6.ai/version. Check logs if it is not updated.
- Release any documentation that may not yet have been released.
- Upgrade issue status to 'Done' in any relevant issue tracker.
- Check if nodes are online, and restart them to update to the latest version
  if desired.
