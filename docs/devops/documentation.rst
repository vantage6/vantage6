.. _documentation:

Documentation
=============

The vantage6 framework is documented on this website. This page describes how
this documentation is created and how to build the documentation locally.

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

    # install requirements to run documentation (only required once)
    pip install -r docs/requirements.txt

    # run documentation interactively
    make devdocs
    # or alternatively, if you don't have make
    sphinx-autobuild docs docs/_build/html --watch .

Then, you can access the documentation on ``http://127.0.0.1:8000``. The ``--watch``
option makes sure that if you make changes to either the documentation text or the
docstrings, the documentation pages will also be reloaded.

.. note::

    The command ``make devdocs`` does *not* build the function documentation by default,
    because building that interactively is slow. If you need to build the function
    documentation locally, you can do so by either running ``make html`` or
    ``make devdocs FUNCTIONDOCS=true``.

.. note::

    This documentation also includes some UML diagrams which are generated using
    `PlantUML <https://plantuml.com/>`_. To generate these diagrams, you need to
    `install Java <https://www.java.com/en/download/help/download_options.html>`_.
    PlantUML itself is included in the Python requirements, so you do not have to
    install it separately.

This documentation is automatically built and published on a commit (on
certain branches, including ``main``). Both Frank and Bart have access to the
vantage6 project when logged into readthedocs. Here they can manage which
branches are to be synced, manage the webhook used to trigger a build, and some
other -less important- settings.

The files in this documentation use the ``rst`` format, to see the syntax view
`this cheatsheet <https://github.com/ralsina/rst-cheatsheet/blob/master/rst-cheatsheet.rst>`_.
