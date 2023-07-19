.. _documentation:

Documentation
=============

The vantage6 framework is documented on this website.
Additionally, there is :ref:`oas3`. This documentation is
shipped directly  with the server instance. All of these documentation pages are
described in more detail below.

How this documentation is created
---------------------------------

The source of the documentation you are currently reading is located
`here <https://github.com/vantage6/vantage6/tree/main/docs/>`_, in the ``docs``
folder of the *vantage6* repository itself.

To build the documentation locally, there are two options. To build a static
version, you can do ``make html`` when you are in the ``docs`` directory.
If you want to automatically refresh the documentation whenever you make a
change, you can use `sphinx-autobuild <https://pypi.org/project/sphinx-autobuild/>`_.
Assuming you are in the main directory of the repository, run the following
commands:

::

    pip install -r docs/requirements.txt
    sphinx-autobuild docs docs/_build/html --watch .

Of course, you only have to install the requirements if you had not done so
before.

Then you can access the documentation on ``http://127.0.0.1:8000``. The
``--watch`` option makes sure that if you make changes to either the
documentation text or the docstrings, the documentation pages will also be
reloaded.

.. TODO review part below
This documentation is automatically built and published on a commit (on
certain branches, including ``main``). Both Frank and Bart have access to the
vantage6 project when logged into readthedocs. Here they can manage which
branches are to be synced, manage the webhook used to trigger a build, and some
other -less important- settings.

The files in this documentation use the ``rst`` format, to see the syntax view
`this cheatsheet <https://github.com/ralsina/rst-cheatsheet/blob/master/rst-cheatsheet.rst>`_.

.. _oas3:

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

