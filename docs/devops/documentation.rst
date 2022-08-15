.. _documentation:
Documentation
=============

We maintain 2 documentation spaces. The *user* documentation which is intended for the end users of vantage6 and the *technical* documentation where you are right now. We also document the API using OAS3+, which ships with the server instance.

User documentation
------------------
The user documentation can be found at `docs.vantage6.ai <https://docs.vantage6.ai>`_. It is hosted at the Gitbook servers for free. The documentation is automatically synced with out `Github <https://github.com/vantage6/gitbook-docs>`_. So in case we need to bail ship and find a new harbor for our user documentation we can use this repository.

There are two ways to edit the documentation:

1. Use the userinterface of `Gitbook <https://app.gitbook.com/>`_. You need credentials to do so.
2. Clone the `gitbook-docs <https://github.com/vantage6/gitbook-docs>`_ repository, make edits and commit it back to the repository. Note that as we write this not all gitbook content is synced, see `here <https://github.com/vantage6/vantage6/issues/267>`_

Technical documentation
-----------------------
The source of the technical documentation you are currently reading is located in the *vantage6* repository itself if the ``docs`` folder. The documentation itself is hosted at `tech-docs.vantage6.ai <https://tech-docs.vantage6.ai>`_.

To build the documentation locally you can use the Makefile located in the docs folder. The command ``make html`` will generate these pages in HTML. To automatically build when you make a change you can use `sphinx-autobuild <https://pypi.org/project/sphinx-autobuild/>`_, assuming you are in the main directory:

::

    pip install sphinx-autobuild
    sphinx-autobuild docs docs/_build/html --watch .

Then you can access the documentation on ``http://127.0.0.1:8000``. The ``--watch`` option makes sure that if you make changes to the docstrings the documentation is also reloaded.

The documentation is also automatically build and published on a commit (on certain branches, including ``main``) on readthedocs: `https://tech-docs.vantage6.ai`. Both Frank and Bart have access to the vantage6 project when logged into readthedocs. Here you can manage which branches are synced, the webhook used to trigger a build, and some other -less important- settings.

The files in the documentation use the rst format, to see the syntax view `this cheatsheet <https://github.com/ralsina/rst-cheatsheet/blob/master/rst-cheatsheet.rst>`_.

OAS3+ (formerly Swagger)
-----------------------------------------
The API documentation is hosted at the server at the ``/apidocs`` endpoint. This documentation is generated from the docstrings using `Flasgger <https://github.com/flasgger/flasgger>`_. The source of this documentation can be found in the docstrings of the API functions.

An example of such a docsting:
  ::

    """Summary of the endpoint
       ---
       description: >-
           Short description on what the endpoint does.
           And which users have access or which permissions are required.

       parameters:
           - in: path
             name: id
             schema:
               type: integer
             description: task id
             required: true

       responses:
           200:
               description: Ok
           401:
               description: Unauthorized or missing permission

       security:
           - bearerAuth: []

       tags: ["Group"]
    """

