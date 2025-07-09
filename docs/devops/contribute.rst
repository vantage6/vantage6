.. _contribute:

Contribute
==========

Support questions
-----------------
If you have questions, you can find us on `Discord <https://discord.gg/yAyFf6Y>`_.

We prefer that you ask questions via Discord instead of creating Github
issues. The issue tracker is intended to address bugs, feature requests, and
code changes.

Reporting issues
----------------
Issues can be posted at our `Github issue page <https://github.com/vantage6/vantage6/issues>`_.

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

Community sprints
-----------------

We organize community sprints to work on new features and bug fixes. In cycles of four
weeks, we work across multiple organizations to improve the vantage6 infrastructure.
We work [sprint boards](https://github.com/orgs/vantage6/projects/1) where we track
the progress of the issues that are scheduled for the sprint. Each sprint starts with a
planning meeting where we decide which issues we will work on. At the end of the sprint,
we have a review meeting where we discuss the progress.

The sprints are open to any developer who wants to contribute significantly to the
infrastructure during that period. It is possible to decide per sprint whether you want
to participate or not. Please reach out on `Discord <https://discord.gg/yAyFf6Y>`_ if
you want to join one or more sprints.

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

Code style
^^^^^^^^^^

We use `black <https://black.readthedocs.io/en/stable/index.html>`_ to format
our code. It is important that you use this style so make sure that your
contribution will be easily incorporated into the code base.

Black is automatically installed into your python environment
when you run ``make install-dev``. To automatically enable black, we recommend
that you install the `Black Formatter` extension from Microsoft in the VSCode
marketplace. By enabling the option 'format on save' you can then automatically
format your code in the proper style when you save a file.

Alternatively, or additionally, you may install a pre-commit hook that will
automatically format your code when you commit it. To do so, run the following
command:

  ::

    pre-commit install

You may need to run ``pre-commit autoupdate`` to update the pre-commit hook.

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

Verifying local code changes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

While working on a new feature, it can be useful to run a server and/or nodes
locally with your code changes to verify that it does what you expect it to do.

.. note::

    Since version 5 the local development requires Devspace, this replaces the old
    way where you had to specify `--mount-src` and `--image` options.




This can be done by using the commands ``v6 server`` and ``v6 node`` in
combination with the options ``--mount-src`` and optionally ``--image``.

* The ``--mount-src /path/to/vantage6`` option will overwrite the code that
  the server/node runs with your local code when running the docker image.
  The provided path should point towards the root folder of the `vantage6
  repository <https://github.com/vantage6/vantage6>`_ - where you have your
  local changes.
* The ``--image <url_to_docker_image>`` can be used to point towards a custom
  Docker image for the node or server. This is mostly useful when your code
  update includes dependency upgrades. Then, you need to build a custom
  infrastructure image as the 'old' image does not contain the new depencey and
  the ``--mount-src`` option will only overwrite the source code and not
  re-install dependencies.

Often, it is helpful to run the server and nodes locally with the ``v6 dev``
:ref:`commands <local-test>` to test your changes. With those commands, you can run quickly setup
and manage a local network to test your changes. If you are working on a change in the
server, note that you should still restart the server with ``--mount-src`` and/or
``--image`` to apply your changes, but the ``v6 dev`` commands can be used to quickly
generate nodes and start a UI so that testing your changes is easier.

.. note::

  If you are using Docker Desktop (which is usually the case if you are on
  Windows or MacOS) and want to setup a test environment, you should use
  ``http://host.docker.interal`` for the server address in the node
  configuration file. You should not use ``http://localhost`` in that case as
  that points to the localhost within the docker container instead of the
  system-wide localhost.

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
* **Function docstrings**
  These should always be documented using the
  `numpy format <https://numpydoc.readthedocs.io/en/latest/format.html>`_.
  Such docstrings can then be used to automatically generate parts of the
  technical documentation space.


Roles in the vantage6 community
-------------------------------

As an open-source community, vantage6 is open to constructive development efforts from
anyone. Developers that contribute regularly may at some point become official
members and as such can get more permissions. This section outlines the rules that we
follow as a community to govern this process.

Community access tiers
^^^^^^^^^^^^^^^^^^^^^^

A few levels of access are discerned within the vantage6 community:

- **Contributors**: people that have opened pull requests which have been merged
- **Members**: members of the vantage6 Github organization
- **Administrators**: administrators of the vantage6 Github organization

Contributor access is available to anyone that wants to contribute to vantage6. They
can create their own forks of the vantage6 repository and create pull requests from
there.

Membership gives developers more extensive access, for instance to create branches
within the official repository and view private repositories within the vantage6
Github organization. Membership may be given to anyone that requests it and will be
granted if the majority of the vantage6 members approves of this. There are no hard
requirements for membership: usually, making several contributions helps in receiving
membership, but someone may also attain membership if they are, for instance, an
employee of a trusted organization that plans to invest in vantage6.

Administrator level access gives developers access to merge pull requests into the main
branch and execute other sensitive actions within the repositories. This level of access
will only be granted to a small number of developers that have demonstrated their
knowledge of vantage6 extensively. Administrator access will only be given if all
administrators agree unanimously that it should be granted. In rare cases, administrator
access may also be revoked if the other administrators unanimously agree that it should
be revoked.

Voting for membership and administrator access may be done in the community meetings,
but can also be done asynchronously via email.