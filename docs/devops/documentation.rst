Documentation
=============

We maintain 2 documentation pages. The **user** documentation which is intended for the end users of vantage6 and the technical documentation where you are right now.

User documentation
------------------
The user documentation can be found at `docs.vantage6.ai <https://docs.vantage6.ai>`_. It is hosted at the Gitbook servers for free. The documentation is automatically synced with out `Github <https://github.com/vantage6/gitbook-docs>`_. So in case we need to bail ship and find a new harbor for our user documentation we can use this repository.

There are two ways to edit the documentation:

1. Use the userinterface of `Gitbook <https://app.gitbook.com/>`_. You need credentials to do so.
2. Clone the `gitbook-docs <https://github.com/vantage6/gitbook-docs>`_ repository, make edits and commit it back to the repository. Note that as we write this not all gitbook content is synced, see `here <https://github.com/vantage6/vantage6/issues/267>`_

Technical documentation
-----------------------
The source of the technical documentation you are currently reading is located in the *vantage6* repository itself if the ``docs`` folder.

To build the documentation locally you can use the Makefile located in the docs folder. The command ``make html`` will generate these pages in HTML.

The documentation is also automatically build and published on a commit (on certain branches, including ``main``) on readthedocs: `https://tech-docs.vantage6.ai`. Both Frank and Bart have access to the vantage6 project when logged into readthedocs. Here you can manage which branches are synced, the webhook used to trigger a build, and some other -less important- settings.

The files in the documentation use the rst format, to see the syntax view this cheatsheet: `https://github.com/ralsina/rst-cheatsheet/blob/master/rst-cheatsheet.rst`.

