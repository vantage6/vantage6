Release
=======

.. _format:

Version format
--------------
Semantic versioning is used: ``Major.Minor.Patch.Pre[N].Post<n>``.

**Major** is used for releasing breaking changes. For example, when the database
  model has changed, a new major version will be issued.

**Minor** is used for releasing new features, enhancements and other changes that
  are compatible with all other components. An example is the release of an
  additional endpoint.

**Patch** is used for bugfixes and other minor changes

**Pre[N]** is used for alpha (a), beta (b) and release candidates (rc) releases and the
  build number is appended (e.g. ``2.0.1b1`` indicates the first beta-build)

**Post[N]** is used for a rebuild where no code changes have been made, but where
  for example a dependency has been updated and a rebuild is required. This
  applies only to creating Docker images and not to github or PyPi releases.

.. warning::
   Post releases are only used by versioning the Docker images.
   Code changes should never be released with a ``.post[N]`` version.

Create a release
----------------
To create a new release, one should go through the following steps:

* Check out the correct branche of the `vantage6 <https://github.com/vantage6/vantage6>`_ repository and pull the latest version:

  ::

    $ git checkout main
    $ git pull

* Create a tag for the release. See :ref:`format` for more details on version names:

  ::

    $ git tag version/x.y.z

* Push the tag to the remote. This should trigger the release pipeline on Github:

  ::

    $ git push origin version/x.y.z

What does the release pipeline do?
----------------------------------
The release pipeline executes the following steps:

1. It checks if the tag contains a valid version specification, cancel if not
2. Update the version in the repository code according to the tag
3. Install the dependencies and build the Python package
4. Upload the package to PyPi
5. Build and push the docker image to harbor2.vantage6.ai
6. Post a message in Discord to alert the community of the new release. This is not done if the version is a release candidate (e.g. version/x.y.0rc1)

If you specify a tag with a version that already exists, the build pipeline will fail as the upload to PyPi is rejected.

Distribute release
------------------
Nodes and servers that already exist will be automatically upgraded to the latest version of their major release when they are restarted. This happens by pulling the newly released docker image. Note that the major release is never automatically updated: for example, a node running version 2.1.0 will update to 2.1.1, but never to 3.0.0. Depending on the version of Vantage6 that is being used, there is a reserved Docker image tag for distributing the upgrades. These are the following:

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

