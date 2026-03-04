.. include:: <isonum.txt>

.. _user-guide:

User guide
==========

In this section of the documentation, we explain how you can interact with the
vantage6 hub and the nodes as a user.

There are several ways in which you can interact with the vantage6 hub: the
:ref:`ui` (UI), the :ref:`python-client`, and the :ref:`hq-api`. In the sections below,
we describe how to use each of these methods, and what you need to install
(if anything).

For most use cases, we recommend to use the :ref:`ui`, as this requires
the least amount of effort. If you want to automate your workflow, we recommend
using the :ref:`python-client`.

.. warning::
    Depending on the algorithm used in your project, it *may* be required to use a specific
    language to post a task and retrieve the results. This could happen when
    the output of an algorithm contains a language specific datatype and or
    serialization. For instance, if the algorithm returns a numpy array, you need to use
    Python to retrieve the results - and thus you will not be able to see the results in
    the UI.

.. toctree::
    :maxdepth: 3

    ui
    pyclient
    api