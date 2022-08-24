.. _documentation:
Documentation
=============

We maintain two documentation websites. The **user documentation** which is intended for the end users of vantage6, and the **technical documentation**, intended for developers, which you are looking at right now. Additionally, there is **API documentation** using OAS3+. This documentation is shipped directly with the server instance. All of these documentation pages are described in more detail below.

User documentation
------------------
The user documentation can be found at `docs.vantage6.ai <https://docs.vantage6.ai>`_. It is hosted at Gitbook for free. The documentation is automatically synced to this `Github repository <https://github.com/vantage6/gitbook-docs>`_.

There are two ways to edit the documentation:

1. Clone the `gitbook-docs <https://github.com/vantage6/gitbook-docs>`_ repository, make edits and commit it back to the repository. At the time of writing, not all Gitbook content is synced, see `here <https://github.com/vantage6/vantage6/issues/267>`_.
2. Use the user interface of `Gitbook <https://app.gitbook.com/>`_. Note that you need credentials to do so.

Technical documentation
-----------------------
The source of the technical documentation you are currently reading is located `here <https://github.com/vantage6/vantage6/tree/main/docs/>`_, in the ``docs`` folder of the *vantage6* repository itself. The documentation is hosted at `tech-docs.vantage6.ai <https://tech-docs.vantage6.ai>`_.

To build the documentation locally you can use the ``Makefile`` located in the docs folder. The command ``make html`` will generate these pages in HTML. To automatically rebuild the documentation whenever you make a change, you can use `sphinx-autobuild <https://pypi.org/project/sphinx-autobuild/>`_. Assuming you are in the main directory, run the following command:

::

    pip install sphinx-autobuild
    sphinx-autobuild docs docs/_build/html --watch .

Then you can access the documentation on ``http://127.0.0.1:8000``. The ``--watch`` option makes sure that if you make changes to either the documentation text or the docstrings, the documentation pages will also be reloaded.

.. TODO review part below
This documentation is automatically built and published on a commit (on certain branches, including ``main``). Both Frank and Bart have access to the vantage6 project when logged into readthedocs. Here they can manage which branches are to be synced, manage the webhook used to trigger a build, and some other -less important- settings.

The files in this documentation use the rst format, to see the syntax view `this cheatsheet <https://github.com/ralsina/rst-cheatsheet/blob/master/rst-cheatsheet.rst>`_.

API Documenation with OAS3+
-----------------------------------------
The API documentation is hosted at the server at the ``/apidocs`` endpoint. This documentation is generated from the docstrings using `Flasgger <https://github.com/flasgger/flasgger>`_. The source of this documentation can be found in the docstrings of the API functions.

If you are unfamiliar with OAS3+, note that it was formerly known as Swagger.

An example of such a docsting:
  ::

    """Summary of the endpoint
       ---
       description: >-
           Short description on what the endpoint does, and which users have
           access or which permissions are required.

       parameters:
           - in: path
             name: id
             schema:
               type: integer
             description: some identifier
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

