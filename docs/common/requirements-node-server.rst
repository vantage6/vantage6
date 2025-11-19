Below are the minimal requirements for vantage6 infrastructure components. Note
that these are recommendations: it may also work on other
hardware, operating systems, versions of Python etc. (but they are not tested
as much).

**Hardware**

-  x86 CPU architecture + virtualization enabled
-  4 GB memory (minimum)
-  50GB+ storage
-  Stable and fast (1 Mbps+ internet connection)
|requirement-public-ip|

**Software**

-  Operating system: Ubuntu 20.04+ |requirement-OS|
-  Python
-  Helm
- A Kubernetes environment (e.g. Microk8s, Docker Desktop, Kubernets Cluster)

.. note::
    For the server, Ubuntu is highly recommended. It is possible to run a
    development server on Windows or MacOS, but for production purposes we recommend
    using Ubuntu.

.. warning::
    The hardware requirements of the node also depend on the algorithms that
    the node will run. For example, you probably need less compute power for a
    descriptive statistical algorithm than for a machine learning model.

.. _python:

Python
""""""

Installation of any of the vantage6 packages requires Python 3.13.
For installation instructions, see `python.org <https://python.org>`__ or use the
package manager native to your OS and/or distribution.

.. note::
    We recommend you install vantage6 in a new, clean Python environment using uv.

    Higher versions of Python (3.11+) will most likely also work, as might lower
    versions (3.8 or 3.9). However, we develop and test vantage6 on version
    3.13, so that is the safest choice.

.. warning::
    Note that Python 3.13 is only used in vantage6 v5.0.0 and higher. In lower versions,
    Python 3.10 is required. Before vantage6 v3.8.0, Python 3.7 was used.

.. _kubectl:

Kubernetes environment
""""""

A Kubernetes environment is required to run the vantage6 infrastructure. For development
environments, we recommend using Microk8s or Docker Desktop. For production environments,
we recommend using a Kubernetes cluster, or microk8s on a VM. Here are some details on
the different options:
- **Microk8s**: For Ubuntu, we recommend installing
  `Microk8s <https://microk8s.io/docs/getting-started>`_, which is a lightweight
  Kubernetes distribution that is easy to install and use. We recommend using this for
  development environments as well as for deploying nodes. Deploying central
  components (hub, auth, algorithm store) is also possible with Microk8s, but usually
  it would be preferable to use a Kubernetes cluster, e.g for easier scaling.
- **Docker Desktop**: If you are using Docker Desktop, you can simply
  `switch on Kubernetes <https://docs.docker.com/desktop/features/kubernetes/>`_.
  This is useful for development  environments. This is only recommended for development
  environments.
- **Kubernetes Cluster**: For production environments, we recommend using a Kubernetes
  cluster. There are numerous cloud providers that offer Kubernetes as a service. An
  example is the `Azure Kubernetes Service <https://azure.microsoft.com/en-us/products/kubernetes-service>`_
  but there are many others.


.. note::

  To use vantage6, you also need to install Kubectl. Usually, though, this comes
  with your Kubernetes distribution. Kubectl is a command line tool for
  managing Kubernetes clusters, which is used to manage the vantage6 Kubernetes
  resources.

Helm
""""

`Helm <https://helm.sh/docs/intro/install/>`_ is a package manager for Kubernetes. It
is used to deploy and manage the Kubernetes resources for the vantage6 infrastructure.
The vantage6 infrastructure is available in several Helm charts. Therefore, you need
``helm`` to deploy and manage the Kubernetes resources for the vantage6 infrastructure.
