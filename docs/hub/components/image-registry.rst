Image registry
==============

The image registry is a service that allows you to store and retrieve images.


.. _docker-registry:

Docker registry
"""""""""""""""

A Docker registry or repository provides storage and versioning for Docker
images. Installing a private Docker registry is useful if you don't want to
share your algorithms. Also, a private registry may have security benefits,
for example, you can scan your images for vulnerabilities and you can limit
the range of IP addresses that the node may access to the vantage6 hub and the
private registry.

.. note::

  If you use your own registry, make sure that it conforms to the
  `OCI distribution specification <https://distribution.github.io/distribution/spec/api/>`_.
  This specification is supported by all major container registry providers, such
  as Docker Hub, Harbor, Azure Container Registry and Github container registry.

The image registry is not really a part of the vantage6 infrastructure. You should
install and configure your own image registry, depending on your needs. Below, we list
some of the most popular image registries that we recommend.

Harbor
~~~~~~

Our preferred solution for hosting a Docker registry is
`Harbor <https://goharbor.io>`_, which is part of the open source-based
`Cloud Native Computing Foundation <https://cncf.io>`_. Harbor provides access control, a user
interface and automated scanning on vulnerabilities.

Github container registry
~~~~~~~~~~~~~~~~~~~~~~~~~~

`Github container registry <https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry>`_
is a free Docker registry provided by Github. It is a good solution for hosting
your algorithms, especially if you are using Github for your code.

Docker Hub
~~~~~~~~~~

Docker itself provides a registry as a turn-key solution on Docker Hub.
Instructions for setting it up can be found here:
https://hub.docker.com/_/registry.

Note that some features of vantage6, such as timestamp based retrieval of the
newest image, or multi-arch images, are not supported by the Docker Hub
registry.

.. note::

  If you are using a private docker registry, your nodes need to login to it in order
  to be able to retrieve the algorithms. You can do this by adding the following
  to the node configuration file:

  .. code:: yaml

      private_docker_registries:
        - registry: docker-registry.org
          username: docker-registry-user
          password: docker-registry-password