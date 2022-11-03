Release
=======

This page is intended to provide information about our release process. First,
we discuss the version formatting, after which we discuss the actual creation
and distribution of a release.

.. _format:

Version format
--------------
Semantic versioning is used: ``Major.Minor.Patch.Pre[N].Post<n>``.

**Major** is used for releasing breaking changes. For example, when the database
  model has changed, a new major version should be issued.

**Minor** is used for releasing new features, enhancements and other changes that
  are compatible with all other components. An example is the release of a new endpoint.

**Patch** is used for bugfixes and other minor changes

**Pre[N]** is used for alpha (a), beta (b) and release candidates (rc) releases and the
  build number is appended (e.g. ``2.0.1b1`` indicates the first beta-build of version ``2.0.1``)

**Post[N]** is used for a rebuild where no code changes have been made, but where,
  for example, a dependency has been updated and a rebuild is required.

.. warning::
   Post releases are only used by versioning the Docker images.
   Code changes should never be released with a ``.post[N]`` version.

Create a release
----------------
To create a new release, one should go through the following steps:

* Check out the correct branch of the `vantage6 <https://github.com/vantage6/vantage6>`_ repository and pull the latest version:

  ::

    $ git checkout main
    $ git pull

* Create a tag for the release. See :ref:`format` for more details on version names:

  ::

    $ git tag version/x.y.z

* Push the tag to the remote. This will trigger the release pipeline on Github:

  ::

    $ git push origin version/x.y.z

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

.. list-table:: Environment variables
   :widths: 30 70
   :header-rows: 1

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
    * - Token to post a message to the Discord community when a new release is
        published.

Distribute release
------------------
Nodes and servers that are already running will automatically be upgraded to
the latest version of their major release when they are restarted. This
happens by pulling the newly released docker image. Note that the major
release is never automatically updated: for example, a node running version
2.1.0 will update to 2.1.1 or 2.2.0, but never to 3.0.0. Depending on the
version of Vantage6 that is being used, there is a reserved Docker image tag
for distributing the upgrades. These are the following:

+---------------+------------------------+
| Tag           | Description            |
+===============+========================+
| petronas      | ``3.x.x`` release      |
+---------------+------------------------+
| harukas       | ``2.x.x`` release      |
+---------------+------------------------+
| troltunga     | ``1.x.x`` release      |
+---------------+------------------------+

Docker images can be pulled manually with e.g.

::

  $ docker pull harbor2.vantage6.ai/infrastructure/server:petronas
  $ docker pull harbor2.vantage6.ai/infrastructure/node:3.1.0

User Interface release
----------------------
The release process for the user interface (UI) is very similar to the release
of the infrastructure detailed above. The same versioning format is used, and
when you push a version tag, the automated release process is triggered.

We have synchronized the version of the UI with that of the infrastructure. In
case we create a new release of the UI without updating the infrastructure, we
do so via a post release, i.e. `version/x.y.z-post1` for the first post release.

The release pipeline for the UI executes the following steps:

1. Version tag is verified (same as infrastructure)
2. Version is updated in the code (same as infrastructure)
3. Application is built
4. Application is pushed to our UI deployment slot (an Azure app service)