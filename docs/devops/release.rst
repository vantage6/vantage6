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
2. *Install the release*. The release should be tested from a clean environment.

  .. code:: bash

    uv venv --python 3.13
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    uv pip install vantage6==<version>

3. *Start server and nodes*. Start the server, nodes, UI and algorithm store for the
   release candidate using a ``v6 sandbox`` network:

  .. code:: bash

    v6 sandbox new \
        --server-image harbor2.vantage6.ai/infrastructure/server:<version> \
        --ui-image harbor2.vantage6.ai/infrastructure/ui:<version> \
        --node-image harbor2.vantage6.ai/infrastructure/node:<version> \
        --store-image harbor2.vantage6.ai/infrastructure/algorithm-store:<version>

4. *Test code changes*. Go through all issues that are part of the new release
   and test if they work as intended.

5. *Run test algorithms*. The algorithm `v6-feature-tester` is run and checked.
   This algorithm checks several features to see if they are performing as
   expected. Additionaly, the `v6-node-to-node-diagnostics` algorithm is run
   to check the VPN functionality.

6. *Update algorithms*. For some releases, algorithms have to be updated, either because
   they no longer work in the new version of vantage6, or, less urgently, if the
   algorithm store is extended so new metadata on the algorithm can be stored. updating
   the algorithms is especially important for the algorithms in the community store, as
   these are used by the entire vantage6 community.

7. *Stop the network*. After testing is finished, you can stop the network and clean up:

  .. code:: bash

    v6 sandbox stop
    v6 sandbox remove

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
5. Build and push the Docker images and Helm charts to `harbor2.vantage6.ai
   <https://harbor2.vantage6.ai>`_.
6. Post a message in Discord to alert the community of the new release. This
   is not done if the version is a pre-release (e.g. version/x.y.0rc1).

.. note::

    All vantage6 infrastructure components (server, node, store, UI, etc.) are released
    at the same time, with the same version number.

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
Central components (server, auth, store, UI) that are already running will automatically
be upgraded to the latest version of their major release when they are restarted, unless otherwise
specified in the respective configuration files. Nodes behave similarly, but instead of
picking the latest version, they check which version the server is running and update to
that (minor) version. The update to the new version happens by pulling the newly
released Helm charts and Docker images.

Note that the major
release is never automatically updated: for example, a node running version
4.1.0 will update to 4.1.1 or 4.2.0, but never to 5.0.0. Depending on the
version of vantage6 that is being used, there is a reserved Docker image tag
for distributing the upgrades. These are the following:

+---------------+------------------------+
| Tag           | Description            |
+===============+========================+
| uluru         | ``5.x.x`` release      |
+---------------+------------------------+
| cotopaxi      | ``4.x.x`` release      |
+---------------+------------------------+
| petronas      | ``3.x.x`` release      |
+---------------+------------------------+
| harukas       | ``2.x.x`` release      |
+---------------+------------------------+
| troltunga     | ``1.x.x`` release      |
+---------------+------------------------+


Post-release checks
-------------------

After a release, there are a few checks that are performed. Most of these are
only relevant if you are hosting a server yourself that is being automatically
updated upon new releases, as is for instance the case for the Uluru server.

For Uluru, the following checks are done:

- Check that harbor2.vantage6.ai has updated images ``server:uluru``,
  ``server:uluru-live`` and ``node:uluru``.
- Check if the (live) server version is updated. Go to:
  https://uluru.vantage6.ai/version. Check logs if it is not updated.
- Release any documentation that may not yet have been released.
- Upgrade issue status to 'Done' in any relevant issue tracker.
- Check if nodes are online, and restart them to update to the latest version
  if desired.
