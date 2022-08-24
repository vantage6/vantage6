Contribute
==========

Support questions
-----------------
If you have questions, you can use

* `Github discussions <https://github.com/vantage6/vantage6/discussions>`_
* Ask us on `Discord <https://discord.gg/yAyFf6Y>`_

We prefer that you ask questions via these routes rather than creating Github issues. The issue tracker is intended to address bugs, feature requests, and code changes.

Reporting issues
----------------
Issues can be posted at our `Github issue <https://github.com/vantage6/vantage6/issues>`_ page. Please use one of the templates:

* Bug report: you encountered broken code
* Feature request: you want something to be added
* Change request: there is a something you would like to be different but it is not considered a new feature nor is something broken

Using these templates makes it easier for us to manage the projects. You can see what we are working on here:

* `Sprints <https://github.com/orgs/vantage6/projects/1>`_
* `Hotfixes <https://github.com/orgs/vantage6/projects/2>`_
* `Feature requests <https://github.com/orgs/vantage6/projects/3>`_

Planning
--------
We plan to organize meetings periodically to coordinate and plan the development efforts of the vantage6 community. More information on this will follow later.

Submitting patches
------------------
If there is not an open issue for what you want to submit, please open one for discussion before submitting the PR. We encourage you to reach out to us on `Discord <https://discord.gg/yAyFf6Y>`_, so that we can work together to ensure your contribution is added to the repository.

Setup your environment
^^^^^^^^^^^^^^^^^^^^^^
* Make sure you have a Github account
* Install and configure git
* (Optional) install and configure Miniconda
* Clone the main repository locally:

  ::

    git clone https://github.com/vantage6/vantage6
    cd vantage6

* Add your fork as a remote to push your work to. Replace ``{username}`` with your username.

  ::

    git remote add fork https://github.com/{username}/vantage6

* Create a virtual environment to work in. For miniconda:

  ::

    conda create -n vantage6 python=3.7
    conda activate vantage6

  It is also possible to use ``virtualenv`` if you do not have a conda installation.

* Update pip and setuptools

  ::

    python -m pip install --upgrade pip setuptools

* Install vantage6 as development environment with the ``-e`` flag.

  ::

    pip install -e .


Coding
^^^^^^
First, create a branch you can work on. Make sure you branch of the latest ``main`` branch:

  ::

    git fetch origin
    git checkout -b your-branch-name origin/main

Then you can create your bugfix, change or feature. Make sure to commit frequently. Preferably include tests that cover your changes.

Finally, push your commits to your fork on Github and create a pull request.

  ::

    git push --set-upstream fork your-branch-name

Please apply the `PEP8 <https://peps.python.org/pep-0008/>`_ standards to your code.

Local test setup
^^^^^^^^^^^^^^^^
To test your code changes, it may be useful to create a local test setup. There are several ways of doing this.

1. Use the command ``vserver-local`` and ``vnode-local``. This runs the application in your current activated Python environment.
2. Use the command ``vserver`` and ``vnode`` in combintation with the options ``--mount-src`` and optionally ``--image``.
  * The ``--mount-src`` option will run your current code in the docker image. The provided path should point towards the root folder of the `vantage6 repository <https://github.com/vantage6/vantage6>`_.
  * The ``--image`` can be used to point towards a custom build infrastructure image. Note that when your code update includes dependency upgrades you need to build a custom infrastructure image as the 'old' image does not contain these and the ``--mount-src`` option will only overwrite the source and not re-install dependencies.

.. note::

  If you are using Docker Desktop (which is usually the case if you are on Windows or MacOS) and want to setup a test environment, you should use ``http://host.docker.interal`` for the server address in the node configuration file. You should not use ``http://localhost`` in that case as that points to the localhost within the docker container instead of the system-wide localhost.

Unit tests & coverage
^^^^^^^^^^^^^^^^^^^^^
You can execute unit tests them using the ``test`` command in the Makefile:

  ::

    make test

If you want to execute a specific unit test (e.g. the one you just created or one that is failing), you can use a command like:

  ::

    python -m unittest tests_folder.test_filename.TestClassName.test_name

Unless you are inside the ``tests_folder``, then you should remove that section.

When you submit your PR, the automated pipeline `Github actions <https://github.com/vantage6/vantage6/actions/workflows/unit_tests.yml>`_ both runs the unit tests and computes the coverage.


Documentation
^^^^^^^^^^^^^
Depending on the changes you made, you may need to add a little (or a lot) of documentation.

* **User documentation.**
  Update it if your change led to a different expierence for the end-user
* **Technical documentation.**
  Update it if you added new functionality. Write up your functionality in the :doc:`../server/server` and/or :doc:`../node/node` sections, and check if the docstrings of any functions you added are properly reflected in the :doc:`../api/` section.
* **OAS (Open API Specification).**
  If you changed input/output for any of the API endpoints, make sure to add it to the docstrings in the `OAS3+ format <https://swagger.io/specification/>`_. Also, please verify that when you run the server, the specification on ``http://{localhost}:{port}/apidocs`` is correct.

Functions should always be documented using the `numpy format <https://numpydoc.readthedocs.io/en/latest/format.html>`_ as such docstrings can be used in this technical documentation space.

For more information on how and where to edit the documentation, see the section :doc:`documentation`.
