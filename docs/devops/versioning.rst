Versioning
==========

Format
------
In vantage6 semantic versioning is used: ``Major.Minor.Patch.Pre<m>.Post<n>``.

* Major is used for releasing breaking changes. For example, when the database
  model has changed, a new major version will be issued.
* Minor is used for releasing new features, enhancements and other changes that
  are compatible with all other components. An example is the release of an
  additional endpoint.
* Patch is used for bugfixes and other minor changes Pre is used for alpha (a),
  beta (b) and release candidates (rc) releases and the build number is
  appended (e.g. 2.0.1b1 indicates the first beta-build)
* Post is used for a rebuild where no code changes have been made, but where
  for example a dependency has been updated and a rebuild is required. This
  applies only to creating Docker images and not to github or PyPi releases.

::

  Post releases are only used by versioning the Docker images.
  Code changes should never be released with a post<n> version.
