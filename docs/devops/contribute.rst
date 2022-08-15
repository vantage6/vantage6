How to contribute to vantage6
=============================

Support questions
-----------------
Please do not use the issue tracker for asking questions. The issue tracker is intended to address bugs, feature requests, and code changes. If you have questions, you can use

* `Github discussions <https://github.com/vantage6/vantage6/discussions>`_
* Ask us on `Discord <https://discord.gg/yAyFf6Y>`_

Reporting issues
----------------
Issues can be posted at our `Github Issue <https://github.com/vantage6/vantage6/issues>`_ page. Please use one of the templates:

* Bug report, you encountered broken code
* Feature request, you want something to be added
* Change request, there is a something you would like to be different but is not considered a new feature and its not something broken

When using the templates, it is easier for us to manage the projects. You can see what we are working on here:

* `Sprints <https://github.com/orgs/vantage6/projects/1>`_
* `HOTFIX <https://github.com/orgs/vantage6/projects/2>`_
* `Feature-requests <https://github.com/orgs/vantage6/projects/3>`_

Submitting patches
------------------
If there is not an open issue for what you want to submit, open one for discussion before submitting the PR. We encourage you to also discuss with us on `Discord <https://discord.gg/yAyFf6Y>`_, so that we together make sure your contribution is added to the repository.

Setup
^^^^^
* Make sure you have a Github account
* Install and configure git
* (Optional) Install and configure Miniconda
* Clone the main repository locally:

  ::

    $ git clone https://github.com/vantage6/vantage6
    $ cd vantage6

* Add your fork as a remote to push your work to. Replace ``{username}`` with your username.

  ::

    $ git remote add fork https://github.com/{username}/vantage6

* Create a virtual environment to work in. For miniconda:

  ::

    $ conda create -n vantage6 python=3.7
    $ conda activate vantage6

  it is also possible to use virtualenv if you did not install conda.

* Update pip and setuptools

  ::

    $ python -m pip install --upgrade pip setuptools

* Install vantage6 as development environment

  ::

    $ pip install -e .


Coding
^^^^^^
First create a branch you can work on. Make sure you branch of the latest ``main`` branch:

  ::

    $ git fetch origin
    $ git checkout -b your-branch-name origin/main

  ..
    I am not competely sure if you need to branch of main when submitting a bugfix?

Then you can create your bugfix, change or feature. Make sure to commit frequently. Preferably include tests that cover your changes.

Finally, push your commits to your fork on Github and create a pull request.

  ::

    $ git push --set-upstream fork your-branch-name

A few notes on coding:
* Use the `PEP008 <https://peps.python.org/pep-0008/>`_ standards
* ...

Testing & coverage
^^^^^^^^^^^^^^^^^^
If you added unittest you can test them using the ``test`` command in the Makefile:

  ::

    $ make test

When you submit your PR, unittests run and the coverage is computed automatically by `Github actions <https://github.com/vantage6/vantage6/actions>`_.


Documentation
^^^^^^^^^^^^^
Depending where you made changes you need to add a little or a lot of documentation.

*  User documentation
   Your change led to a different expierence for the end-user
*  Technical documentation
   If you added new functionality it is good to check if you need to add anything to the :doc:`server` or :doc:`node` sections
* OAS (Open API Specification)
   If you changed input/output for any of the API endpoints, make sure to add it to the docstrings in the `OAS3+ format <https://swagger.io/specification/>`_. And verify that when you run the server the specification is correct by checking ``http://{localhost}:{port}/apidocs``

Functions are always documented using the `numpy format <https://numpydoc.readthedocs.io/en/latest/format.html>`_. These docstrings can be used in this technical documentation space.

For more information on how and where to edit the documentation, see the section :doc:`documentation`.
