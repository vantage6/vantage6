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
-  Python v3.13
-  Helm
- A Kubernetes environment (e.g. Microk8s, Docker Desktop, Kubernetes Cluster)

Below, we provide more details on the software requirements.

.. note::
    |installation-note|

.. _python:

Python
""""""

Installation of any of the vantage6 packages requires Python 3.13.
For installation instructions, see `python.org <https://python.org>`__ or use the
package manager native to your OS and/or distribution.

.. note::
    We recommend you install vantage6 in a new, clean Python environment.

    Higher versions of Python (3.14+) will most likely also work, as might lower
    versions. However, we develop and test vantage6 on version 3.13, so that is the
    best choice.

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
  development environments as well as for deploying nodes. Deploying the central hub
  components (HQ, auth, algorithm store) is also possible with Microk8s, but usually
  it would be preferable to use a Kubernetes cluster, e.g for easier scaling.
- **Docker Desktop**: If you are using Docker Desktop, you can simply
  `switch on Kubernetes <https://docs.docker.com/desktop/features/kubernetes/>`_.
  This is useful for development  environments. This is only recommended for development
  environments.
- **Kubernetes Cluster**: For production environments, we recommend using a Kubernetes
  cluster. There are numerous cloud providers that offer Kubernetes as a service. An
  example is the `Azure Kubernetes Service <https://azure.microsoft.com/en-us/products/kubernetes-service>`_
  but there are many others, including those from
  `European providers <https://european-alternatives.eu/category/managed-kubernetes-services>`_.


.. note::

  To use vantage6, you also need to install ``kubectl``. Usually, though, this comes
  with your Kubernetes distribution. ``kubectl`` is a command line tool for
  managing Kubernetes clusters. Vantage6 uses it to manage the vantage6 Kubernetes
  resources.

Helm
""""

`Helm <https://helm.sh/docs/intro/install/>`_ is a package manager for Kubernetes. It
is used to deploy and manage the Kubernetes resources for the vantage6 infrastructure.
The vantage6 infrastructure is available in several Helm charts. Therefore, you need
``helm`` to deploy and manage the Kubernetes resources for the vantage6 infrastructure.

Docker Hardened Images Registry
"""""""""""""""""""""""""""""""

.. note::

   For more information on Docker Hardened Images, see the `Docker Hardened
   Images documentation <https://docs.docker.com/dhi/how-to/use/>`_.

Some vantage6 init containers use images from the `Docker Hardened Images
<https://dhi.io>`_ registry. The following images are affected:

- ``dhi.io/curl:8-alpine`` -- used for HTTP health checks in HQ and algorithm store init containers
- ``dhi.io/kubectl:1`` -- used for Keycloak readiness checks
- ``dhi.io/busybox:1`` -- used for volume permission initialization in the Prometheus deployment
- ``dhi.io/prometheus:3.13`` -- used for the Prometheus deployment

These are Docker's "Community" tier hardened images. Authentication to
``dhi.io`` is required to pull them. You can authenticate using your
`Docker ID <https://docs.docker.com/docker-hub/>`_ and password, or by
creating a `personal access token <https://docs.docker.com/security/access-tokens/>`_
on Docker Hub.

If your Kubernetes cluster cannot pull these images, you will see
``ImagePullBackOff`` errors for the affected pods.

To authenticate your cluster, first log in to the ``dhi.io`` registry:

.. code-block:: bash

   docker login dhi.io

Then, create a Kubernetes secret. You can use either an access token or your
Docker ID credentials:

.. code-block:: bash

   kubectl create secret docker-registry dhi-pull-secret \
     --docker-server=dhi.io \
     --docker-username=<your-docker-username> \
     --docker-password=<your-access-token-or-password> \
     --docker-email=<your-email>

Configure the secret as an ``imagePullSecret`` in your Helm values. For example,
in your ``values.yaml``:

.. code-block:: yaml

   global:
     imagePullSecrets:
       - name: dhi-pull-secret

Alternatively, you can override the individual images in your Helm values
to use publicly accessible alternatives, for example:

.. code-block:: yaml

   global:
     wait:
       auth:
         image: "curlimages/curl:8.7.1"
       store:
         image: "curlimages/curl:8.7.1"
