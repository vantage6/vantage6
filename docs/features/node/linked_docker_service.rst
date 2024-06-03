Linked docker containers
------------------------

*Available since version 3.2.0*

You may have a service running in a Docker container that you would like to make
available to your algorithm. This may be useful, for example, if you are
running a (test) SQL database in a container and want to make it available to
your algorithm without having to set up whitelisting or SSH tunnels.

You can define the container that you want to make available to the algorithm in
the `docker_services` section of your node configuration file:

.. code:: yaml

    docker_services:
        container_label: container_name

where `container_name` is the name of your Docker container. This container will
be made available in the Docker network where the algorithm containers are
running, so your algorithm will be able to access it via `http://localhost`.
The `container_label` will be used as alias for the container in the isolated
Docker network.

Note that this option only works if your container with `container_name` is
already running when you start the node. If it is not, the node will not be able
to link the container to the isolated docker network and will print a warning.