.. _contribute:

Contribute
==========

Support questions
-----------------
If you have questions, you can use

* `Github discussions <https://github.com/vantage6/vantage6/discussions>`_
* Ask us on `Discord <https://discord.gg/yAyFf6Y>`_

We prefer that you ask questions via these routes rather than creating Github
issues. The issue tracker is intended to address bugs, feature requests, and
code changes.

Reporting issues
----------------
Issues can be posted at our `Github issue page <https://github.com/vantage6/vantage6/issues>`_,
or, if you have issues that are specific to the user interface, please post
them to the `UI issue page <https://github.com/vantage6/vantage6-UI/issues>`_.

We distinguish between the following types of issues:

* Bug report: you encountered broken code
* Feature request: you want something to be added
* Change request: there is a something you would like to be different but it
  is not considered a new feature nor is something broken
* Security vulnerabilities: you found a security issue

Each issue type has its own template. Using these templates makes it easier for
us to manage them.

.. warning::

    Security vulnerabilities should not be reported in the Github issue tracker
    as they should not be publically visible. To see how we deal with security
    vulnerabilities read our `policy <https://github.com/vantage6/vantage6/blob/main/SECURITY.md>`_.

    See the :ref:`security-vulnerabilities` section when you want to release a
    security patch yourself.

We distibute the open issues in sprints and hotfixes.
You can check out these boards here:

* `Sprints <https://github.com/orgs/vantage6/projects/1>`_
* `Hotfixes <https://github.com/orgs/vantage6/projects/2>`_

When a high impact bug is reported, we will put it on the hotfix board and
create a patch release as soon as possible.

The sprint board tracks which issues we plan to fix in which upcoming release.
Low-impact bugs, new features and changes will be scheduled into a sprint
periodically. We automatically assign the label 'new' to all newly reported
issues to track which issues should still be scheduled.

If you would like to fix an existing bug or create a new feature, check
:ref:`submit-patch` for more details on e.g. how to set up a local development
environment and how the release process works. We prefer that
you let us know you what are working on so we prevent duplicate work.

.. _security-vulnerabilities:

Security vulnerabilities
------------------------

If you are a member of the Vantage6 Github organization, you can create an
security advisory in the `Security <https://github.com/vantage6/vantage6/security/
advisories>`_ tab. See :numref:`advisory` on what to fill in.

If you are not a member, please reach out directly to Frank Martin and/or Bart
van Beusekom, or any other project member. They can then create a security
advisory for you.

.. list-table:: Advisory details
   :name: advisory
   :widths: 33 67
   :header-rows: 1

   * - Name
     - Details
   * - Ecosystem
     - Set to ``pip``
   * - Package name
     - Set to ``vantage6``
   * - Affected versions
     - Specify the versions (or set of verions) that are affected
   * - Patched version
     - Version where the issue is addessed, you can fill this in later when
       the patch is released.
   * - Severity
     - Determine severity score using `this <https://nvd.nist.gov/vuln-metrics/
       cvss/v3-calculator>`__ tool. Then use table :numref:`severity` to
       determine the level from this score.
   * - Common weakness enumerator (CWE)
     - Find the CWE (or multiple) on `this <https://cwe.mitre.org/>`__ website.

.. list-table:: Severity
   :name: severity
   :widths: 33 67
   :header-rows: 1

   * - Score
     - Level
   * - 0.1-3.9
     - Low
   * - 4.0-6.9
     - Medium
   * - 7.0-8.9
     - High
   * - 9.0-10.0
     - Critical

Once the advisory has been created it is possible to create a private fork from
there (Look for the button ``Start a temporary private fork``). This private
fork should be used to solve the issue.

From the same page you should request a CVE number so we can alert dependent
software projects. Github will review the request. We are not sure what this
entails, but so far they approved all advisories.

.. _community-meetings:

Community Meetings
------------------

We host bi-monthly community meetings intended for aligning development
efforts. Anyone is welcome to join although they are mainly intended for
infrastructure and algorithm developers. There is an opportunity to present
what your team is working on an find collaboration partners.

Community meetings are usually held on the third Thursday of the month at 11:00
AM CET on Microsoft Teams. Reach out on `Discord <https://discord.gg/yAyFf6Y>`_
if you want to join the community meeting.

For more information and slides from previous meetings, check our
`website <https://vantage6.ai/community-meetings/>`_.

.. _submit-patch:

Submitting patches
------------------
If there is not an open issue for what you want to submit, please open one for
discussion before submitting the PR. We encourage you to reach out to us on
`Discord <https://discord.gg/yAyFf6Y>`_, so that we can work together to ensure
your contribution is added to the repository.

The workflow below is specific to the
`vantage6 infrastructure repository <https://github.com/vantage6/vantage6>`_.
However, the concepts for our other repositories are the same. Then, modify
the links below and ignore steps that may be irrelevant to that particular
repository.

Setup your environment
^^^^^^^^^^^^^^^^^^^^^^
* Make sure you have a Github account
* Install and configure ``git`` and ``make``
* (Optional) install and configure Miniconda
* Clone the main repository locally:

  ::

    git clone https://github.com/vantage6/vantage6
    cd vantage6

* Add your fork as a remote to push your work to. Replace ``{username}`` with
  your username.

  ::

    git remote add fork https://github.com/{username}/vantage6

* Create a virtual environment to work in. If you are using miniconda:

  ::

    conda create -n vantage6 python=3.10
    conda activate vantage6

  It is also possible to use ``virtualenv`` if you do not have a conda
  installation.

* Update pip and setuptools

  ::

    python -m pip install --upgrade pip setuptools

* Install vantage6 as development environment:

  ::

    make install-dev


Coding
^^^^^^
First, create a branch you can work on. Make sure you branch of the latest
``main`` branch:

  ::

    git fetch origin
    git checkout -b your-branch-name origin/main

Then you can create your bugfix, change or feature. Make sure to commit
frequently. Preferably include tests that cover your changes.

Finally, push your commits to your fork on Github and create a pull request.

  ::

    git push --set-upstream fork your-branch-name

Please apply the `PEP8 <https://peps.python.org/pep-0008/>`_ standards to your
code.

Local test setup
^^^^^^^^^^^^^^^^
To test your code changes, it may be useful to create a local test setup.
This can be done by using the commands ``v6 server`` and ``v6 node`` in
combination with the options ``--mount-src`` and optionally ``--image``.

* The ``--mount-src`` option will run your current code in the docker image.
  The provided path should point towards the root folder of the `vantage6
  repository <https://github.com/vantage6/vantage6>`_.
* The ``--image`` can be used to point towards a custom build infrastructure
  image. Note that when your code update includes dependency upgrades you
  need to build a custom infrastructure image as the 'old' image does not
  contain these and the ``--mount-src`` option will only overwrite the
  source and not re-install dependencies.

.. note::

  If you are using Docker Desktop (which is usually the case if you are on
  Windows or MacOS) and want to setup a test environment, you should use
  ``http://host.docker.interal`` for the server address in the node
  configuration file. You should not use ``http://localhost`` in that case as
  that points to the localhost within the docker container instead of the
  system-wide localhost.

Unit tests & coverage
^^^^^^^^^^^^^^^^^^^^^
You can execute unit tests using the ``test`` command in the Makefile:

  ::

    make test

If you want to execute a specific unit test (e.g. the one you just created or
one that is failing), you can use a command like:

  ::

    python -m unittest tests_folder.test_filename.TestClassName.test_name

This command assumes you are in the directory above ``tests_folder``. If you are
inside the ``tests_folder``, then you should remove that part.

Pull Request
^^^^^^^^^^^^

Please consider first which branch you want to merge your contribution into.
**Patches** are usually directly merged into ``main``, but **features** are
usually merged into a release branch (e.g. ``release/4.1`` for version 4.1.0)
before being merged into the ``main`` branch.

Before the PR is merged, it should pass the following requirements:

* At least one approved review of a code owner
* All `unit tests <https://github.com/vantage6/vantage6/actions/workflows/unit_
  tests.yml>`_ should complete
* `CodeQL <https://docs.github.com/en/code-security/code-scanning/automatically
  -scanning-your-code-for-vulnerabilities-and-errors/about-code-scanning-with-
  codeql>`_ (vulnerability scanning) should pass
* `Codacy <https://app.codacy.com/gh/vantage6/vantage6/dashboard>`_ - Code
  quality checks - should be OK
* `Coveralls <https://coveralls.io/github/vantage6/vantage6>`_ - Code coverage
  analysis - should not decrease


Documentation
^^^^^^^^^^^^^
Depending on the changes you made, you may need to add a little (or a lot) of
documentation. For more information on how and where to edit the documentation,
see the section :doc:`documentation`.

Consider which documentation you need to update:

* **User documentation.**
  Update it if your change led to a different expierence for the end-user
* **Technical documentation.**
  Update it if you added new functionality. Check if your function docstrings
  have also been added (see last bullet below).
* **OAS (Open API Specification).**
  If you changed input/output for any of the API endpoints, make sure to add
  it to the docstrings. See :ref:`oas3` for more details.
* **Function docstrings**
  These should always be documented using the
  `numpy format <https://numpydoc.readthedocs.io/en/latest/format.html>`_.
  Such docstrings can then be used to automatically generate parts of the
  technical documentation space.
