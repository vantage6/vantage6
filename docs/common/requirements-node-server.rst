The (minimal) requirements of the node and server are
similar. Note that these are recommendations: it may also work on other
hardware, operating systems, versions of Python etc. (but they are not tested
as much).

**Hardware**

-  x86 CPU architecture + virtualization enabled
-  1 GB memory
-  50GB+ storage
-  Stable and fast (1 Mbps+ internet connection)
|requirement-public-ip|

**Software**

-  Operating system: Ubuntu 18.04+ |requirement-OS|
-  Python
-  Docker

.. note::
    For the server, Ubuntu is highly recommended. It is possible to run a
    development server (using `v6 server start`) on Windows or MacOS, but for
    production purposes we recommend using Ubuntu.

.. warning::
    The hardware requirements of the node also depend on the algorithms that
    the node will run. For example, you need much less compute power for a
    descriptive statistical algorithm than for a machine learning model.

.. _python:

Python
""""""

Installation of any of the vantage6 packages requires Python 3.10.
For installation instructions, see `python.org <https://python.org>`__,
`anaconda.com <https://anaconda.com>`__ or use the package manager
native to your OS and/or distribution.

.. note::
    We recommend you install vantage6 in a new, clean Python (Conda)
    environment.

    Higher versions of Python (3.11+) will most likely also work, as might lower
    versions (3.8 or 3.9). However, we develop and test vantage6 on version
    3.10, so that is the safest choice.

.. warning::
    Note that Python 3.10 is only used in vantage6 versions 3.8.0 and higher.
    In lower versions, Python 3.7 is required.

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

    For Windows, if you are using Docker Desktop, it may be preferable to limit
    the amount of memory Docker can use - in some cases it may otherwise
    consume much memory and slow down the system. This may be achieved as
    described `here <https://stackoverflow.com/questions/62405765/memory-allocation-to-docker-containers-after-moving-to-wsl-2-in-windows>`__.

.. note::

    * Always make sure that Docker is running while using vantage6!
    * We recommend to always use the latest version of Docker.
