The (minimal) requirements of the node and server are
similar. Note that these are recommendations: it may also work on other
hardware, operating systems, versions of Python etc. (but they are not tested
as much).

**Hardware**

-  x86 CPU architecture + virtualization enabled
-  1 GB memory
-  50GB+ storage
-  Stable and fast (1 Mbps+ internet connection)
-  Public IP address

**Software**

-  Operating system:
   -  Ubuntu 18.04+
   -  MacOS Big Sur+ (only for node)
   -  Windows 10+ (only for node)
-  :ref:`python`
-  :ref:`docker`

.. note::
    Note that it may be possible to run the server on other operating systems
    (e.g. Windows, MacOS) but this is not tested and therefore not recommended.

.. warning::
    The hardware requirements of the node also depend on the algorithms that
    the node will run. For example, you need much less compute power for a
    descriptive statistical algorithm than for a machine learning model.

.. _python:

Python
""""""

Installation of any of the vantage6 packages requires Python 3.7.
For installation instructions, see `python.org <https://python.org>`__,
`anaconda.com <https://anaconda.com>`__ or use the package manager
native to your OS and/or distribution.

.. note::
    We recommend you install vantage6 in a new, clean Python (Conda)
    environment.

    Other version of Python >= 3.6 will most likely also work, but may give
    issues with installing dependencies. For now, we test vantage6 on
    version 3.7, so that is a safe choice.

.. _docker:

Docker
""""""

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

..  warning::

    Note that for **Linux**, some `post-installation
    steps <https://docs.docker.com/engine/install/linux-postinstall/>`__ may
    be required. Vantage6 needs to be able to run docker without ``sudo``,
    and these steps ensure just that.

.. note::

    * Always make sure that Docker is running while using vantage6!
    * We recommend to always use the latest version of Docker.
