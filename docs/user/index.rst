.. include:: <isonum.txt>

.. _user-guide:

User guide
==========

In this section of the documentation, we explain how you can interact with
vantage6 servers and nodes as a user.

There are four ways in which you can interact with the central server: the
:ref:`ui` (UI), the :ref:`python-client`, the :ref:`r-client`, and the
:ref:`server-api`. In the sections below, we describe
how to use each of these methods, and what you need to install (if anything).

For most use cases, we recommend to use the :ref:`ui`, as this requires
the least amount of effort. If you want to automate your workflow, we recommend
using the :ref:`python-client`.

.. warning::
    Note that for some algorithms, tasks cannot yet be created using the UI,
    or the results cannot be retrieved. This is because these algorithms have
    Python-specific datatypes that cannot be decoded in the UI. In this case,
    you will need to use the Python client to create the task and read the
    results.

.. warning::
    Depending on your algorithm it *may* be required to use a specific
    language to post a task and retrieve the results. This could happen when
    the output of an algorithm contains a language specific datatype and or
    serialization.

.. toctree::
    :maxdepth: 3

    ui
    pyclient
    rclient
    api