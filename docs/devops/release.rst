Release
=======

Create a release
----------------
To create a new release, one should go through the following steps:

* | Check out the correct branches of all the repositories (common, server, node, client, and CLI). Make sure that they are up to date and that you have no local changes. This may be done with the Makefile in the master repo:
  | ``make git-checkout BRANCH={your_branch}``
  | ``make git-pull``

* | Make a commit on the master repo
  | ``git add .``
  | ``git commit -m "message"``

* | Create a tag for the release. See   for more details on version names.
  | ``git tag version/x.y.z``

* | Push the tag. This triggers the release pipeline on Github
  | ``git push origin version/x.y.z``

What does the release pipeline do?
----------------------------------
The release pipeline executes the following steps:

1. It checks if the tag contains a valid version number. Cancel if not.
2. Update the version in the repository code
3. Install the dependencies and build the Python package
4. Upload the package to PyPi
5. Build and push the docker image to harbor2.vantage6.ai
6. Post a message in Discord to alert the community of the new release. This is not done if the version is a release candidate (e.g. version/x.y.0rc1)

If you specify a tag with a version that already exists, the build pipeline will fail as the upload to PyPi is rejected

Distribute release
------------------
Nodes and servers that already exist will be automatically upgraded to the latest version of their major release when they are restarted. This happens by pulling the newly released docker image. Note that the major release is never automatically updated: for example, a node running version 2.1.0 will update to 2.1.1, but never to 3.0.0.
Depending on the version of Vantage6 that is being used, there is a reserved Docker image tag. These are the following:

| Docker images can be pulled manually with e.g.
| ``docker pull harbor2.vantage6.ai/infrastructure/server:petronas``
| or
| ``docker pull harbor2.vantage6.ai/infrastructure/node:3.1.0``