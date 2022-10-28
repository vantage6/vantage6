.. _requirements:

Requirements
============

**vantage6** consists of several
`components <../../about-background/introduction.md#components>`__\ that
can be installed. Which component(s) you need depends on your use case.
Also the requirements differ per component.

Client
------

You can interact with the server via the API. You can explore the server
API on ``https://<serverdomain>/apidocs``
(e.g. https://petronas.vantage6.ai/apidocs for Petronas).

You can use any language to interact with the server as long as it
supports HTTP requests. For Python and R we have written wrappers to
simplify the interaction with the server: see the :ref:`client install`
for more details on how to install these.

.. warning::
    Depending on your algorithm it *may* be
    required to use a specific language to retrieve the results. This could
    happen when the output of an algorithm contains a language specific
    datatype and or serialization.

    E.g. when the algorithm is written in R and the output is written back
    in RDS (=specific to R) you would also need R to read the final input.

    **Please consult the developer of your algorithm if this is the case.**

Node & Server
-------------

The (minimal) requirements of the node and server are similar. Note that
not all of these are hard requirements: it could well be that it also
works on other hardware, operating systems, versions of Python etc.

**Hardware**

-  x86 CPU architecture + virtualization enabled
-  1 GB memory
-  50GB+ storage
-  Stable and fast (1 Mbps+ internet connection)
-  Public IP address

**Software**

-  Operating system

   -  Ubuntu 18.04+ or
   -  MacOS Big Sur+
   -  Windows 10

-  :ref:`python`
-  :ref:`docker`

.. warning::
    The hardware requirements of the node also depend on the algorithms that
    the node will run. For example, you need much less compute power for a
    descriptive statistical algorithm than for a machine learning model.

.. _python:

🐍 Python
----------

Installation of any of the **vantage6** packages requires Python 3.7.
For installation instructions, see `python.org <https://python.org>`__,
`anaconda.com <https://anaconda.com>`__ or use the package manager
native to your OS and/or distribution.

.. note::
    We recommend you install **vantage6** in a new, clean Python environment.

.. note::
    Other version of Python >= 3.6 will most likely also work, but may give
    issues with installing dependencies. For now, we test vantage6 on
    version 3.7, so that is a safe choice.

.. _docker:

🐳 Docker
----------

Docker facilitates encapsulation of applications and their dependencies
in packages that can be easily distributed to diverse systems.
Algorithms are stored in Docker images which nodes can download and
execute. Besides the algorithms, both the node and server are also
running from a docker container themselves.

Please refer to `this page <https://docs.docker.com/engine/install/>`__
on how to install Docker. To verify that Docker is installed and running
you can run the ``hello-world`` example from Docker.

.. code:: bash

   docker run hello-world

.. note::
    🐳 Always make sure that Docker is running while
    using vantage6!

    🐳 We recommend to always use the latest version of Docker. {% endhint %}

..  warning::
    Note that for Linux, some `post-installation
    steps <https://docs.docker.com/engine/install/linux-postinstall/>`__ may
    be required. Vantage6 needs to be able to run docker without ``sudo``,
    and these steps ensure just that.
