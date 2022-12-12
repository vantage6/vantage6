.. _algo-concepts:

Concepts
========

Algorithms are executed at the (vantage6-)node. The node receives a computation
task from the vantage6-server. The node will then retrieve the algorithm,
execute it and return the results to the server.

Algorithms are shared using `Docker images <https://docs.docker.com/get-started
/#what-is-a-container-image>`_ which are stored in a `Docker image registry
<https://docs.vantage6.ai/installation/server/docker-registry>`_ which is
accessible to the nodes. In the following sections we explain the fundamentals
of algorithm containers.

1. `Input & output`_
   Interface between the node and algorithm container
2. `Wrappers`_
   Library to simplify and standardized the node-algorithm input and output
3. `Child containers`_
   Creating subtasks from an algorithm container
4. `Networking`_
   Communicate with other algorithm containers and the vantage6-server
5. `Cross language`_
   Cross language data serialization
6. `Package & distribute`_
   Packaging and shipping algorithms

Input & output
--------------
The algorithm runs in an isolated environment within the data station (node).
As it is important to limit the connectivity and accessability for obvious
security reasons. In order for the algorithm to do its work, it is provided
with several resources.

.. note::

    This section describes the current process. Keep in mind that this is
    subjected to be changed. For more information, please see this `Github
    <https://github.com/vantage6/vantage6/issues/154>`_


Environment variables
^^^^^^^^^^^^^^^^^^^^^
The algorithms have access to several environment variables, see :numref:`Environment variables`. These can be used
to locate certain files or to add local configuration settings into the
container.

.. list-table:: Environment variables
   :widths: 30 70
   :header-rows: 1

   * - Variable
     - Description
   * - ``INPUT_FILE``
     - path to the input file. The input file contains the user defined input
       for the algorithms.

   * - ``TOKEN_FILE``
     - Path to the token file. The token file contains a JWT token which can
       be used to access the vantage6-server. This way the algorithm container
       is able to post new tasks and retrieve results.

   * - ``TEMPORARY_FOLDER``
     - Path to the temporary folder. This folder can be used to store
       intermediate results. These intermediate results are shared between all
       containers that have the same run_id. Algorithm containers which are
       created from an algorithm container themselves share the same run_id.

   * - ``HOST``
     - Contains the URL to the vantage6-server.
   * - ``PORT``
     - Contains the port to which the vantage6-server listens. Is used in
       combination with HOST and API_PATH.
   * - ``API_PATH``
     - Contains the api base path from the vantage6-server.
   * - ``[*]_DATABASE_URI``
     - Contains the URI of the local database. The  ``*``  is replaced by the
       key specified in the node configuration file.

.. note::

    Additional environment variables can be specified in the node configuration
    file using the algorithm_env key. These additional variables are forwarded
    to all algorithm containers.

.. TODO::

    Link to additional environment settings

File mounts
^^^^^^^^^^^
The algorithm container has access to several file mounts.

*Input*
    The input file contains the user defined input. The user specifies this when a task is created.

*Output*
    The algorithm should write its output to this file. When the docker
    container exits the contents of this file will be send back to the
    vantage6-server.

*Token*
    The token file contains a JWT token which can be used by the algorithm
    to communicate with the central server. The token can only be used to
    create a new task with the same image, and is only valid while the task
    has not yet been completed.

*Temporary directory*
    The temporary directory can be used by an algorithm container to share
    files with other algorithm containers that:

    -  run on the same node
    -  have the same ``run_id``

    Algorithm containers that origin from another container (a.k.a master
    container or parent container) share the same ``run_id``. i.o. if a user
    creates a task a new ``run_id`` is assigned.

The paths to these files and directories are stored in the environment
variables, which we will explain now.

Wrappers
--------

The algorithm wrapper simplifies and standardizes the interaction
between algorithm and node. The `client
libraries <../../usage/running-analyses/#client-libraries>`__ and the
algorithm wrapper are tied together and use the same standards. The
algorithm wrapper:

-  reads the environment variables and file mounts and supplies these to
   your algorithm.
-  provides an
   `entrypoint <https://docs.docker.com/engine/reference/builder/#entrypoint>`_ for
   the docker container
-  allows to write a single algorithm for multiple types of data sources

The wrapper is language specific and currently we support Python and R.
Extending this concept to other languages is not so complex.

.. figure:: /images/algorithm_wrapper.png

   The algorithm wrapper handles algorithm input and output.

Federated function
^^^^^^^^^^^^^^^^^^^

The signature of your function has to contain ``data`` as the first
argument. The method name should have a ``RPC_`` prefix. Everything that
is returned by the function will be written to the output file.

*Python:*

.. code:: python

   def RPC_my_algorithm(data, *args, **kwargs):
       pass

*R:*

.. code:: r

   RPC_my_algorithm <- function(data, ...) {
   }

.. _wrapper-central-functions:

Central function
^^^^^^^^^^^^^^^^^

It is quite common to have a central part of your federated analysis
which orchestrates the algorithm and combines the partial results. A
common pattern for a central function would be:

1. Request partial models from all participants
2. Obtain the partial models
3. Combine the partial models to a global model
4. (optional) Repeat step 1-3 until the model converges

It is possible to run the central part of the analysis on your own
machine, but it is also possible to let vantage6 handle the central
part. There are several advantages to letting vantage6 handle this:

-  You don't have to keep your machine running during the analysis
-  You don't need to use the same programming language as the algorithm
   in case a language specific serialization is used in the algorithm

.. note::
    Central functions also run at a node and *not* at the server.

In contrast to the federated functions, central functions are not
prefixed. The first argument needs to be ``client`` and the second
argument needs to be ``data``. The ``data`` argument contains the local
data and the ``client`` argument provides an interface to the
vantage6-server.

.. warning::
    The argument data is not present in the R wrapper. This is a consistency
    issue which will be solved in a future release.


.. raw:: html

   <details>
   <summary><a>Example central function in Python</a></summary>

.. code:: python

   def main(client, data, *args, **kwargs):
      # Run a federated function. Note that we omnit the
      # RPC_ prefix. This prefix is added automatically
      # by the infrastructure
      task = client.create_new_task(
         {
            "method": "my_algorithm",
            "args": [],
            "kwargs": {}
         },
         organization_ids=[...]
      )

       # wait for the federated part to complete
       # and return
       results = wait_and_collect(task)

       return results

.. raw:: html

   </details>
   <br>

.. raw:: html

   <details>
   <summary><a>Example central function in R</a></summary>

.. code:: r

   main <- function(client, ...) {
       # Run a federated function. Note that we omnit the
       # RPC_ prefix. This prefix is added automatically
       # by the infrastructure
       result <- client$call("my_algorithm", ...)

       # Optionally do something with the results

       # return the results
       return(result)
   }

.. raw:: html

   </details>

Different wrappers
^^^^^^^^^^^^^^^^^^

The docker wrappers read the local data source and supplies this to your
functions in your algorithm. Currently CSV and SPARQL for Python and a
CSV wrapper for R is supported. Since the wrapper handles the reading of
the data, you need to rebuild your algorithm with a different wrapper to
make it compatible with a different type of data source. You do this by
updating the ``CMD`` directive in the dockerfile.

*CSV wrapper (Python)*

.. code:: docker

   ...
   CMD python -c "from vantage6.tools.docker_wrapper import docker_wrapper; docker_wrapper('${PKG_NAME}')"

*CSV wrapper (R)*

.. code:: r

   ...
   CMD Rscript -e "vtg::docker.wrapper('$PKG_NAME')"

*SPARQL wrapper (Python)*

.. code:: docker

   ...
   CMD python -c "from vantage6.tools.docker_wrapper import sparql_wrapper; sparql_wrapper('${PKG_NAME}')"

Data serialization
^^^^^^^^^^^^^^^^^^

TODO

Mock client
-----------

TODO

Child containers
----------------

When a user creates a task, one or more nodes spawn an algorithm
container. These algorithm containers can create new tasks themselves.

Every algorithm is supplied with a JWT token (see `Input & output`_).
This token can be used to communicate with the vantage6-server. In case
you use a algorithm wrapper, you simply can use the supplied ``Client``
in case you use a :ref:`wrapper-central-functions`.

A child container can be a parent container itself. There is no limit to
the amount of task layers that can be created. It is common to have only
a single parent container which handles many child containers.

.. figure:: /images/container_hierarchy.png

   Each container can spawn new containers in the network. Each
   container is provided with a unique token which they can use to
   communicate to the vantage6-server.

The token to which the containers have access supplies limited permissions to
the container. For example, the token can be used to create additional tasks,
but only in the same collaboration, and using the same image.

Networking
----------

The algorithm container is deployed in an isolated network to reduce their
exposure. Hence, the algorithm it cannot reach the internet. There are two
exceptions:

1. When the VPN feature is enabled on the server all algorithm
   containers are able to reach each other using an ``ip`` and
   ``port`` over VPN.
2. The central server is reachable through a local proxy service. In the
   algorithm you can use the ``HOST``, ``POST`` and ``API_PATH`` to find
   the address of the server.

.. note::
    We are working on a whitelisting feature which allows a node to
    configure addresses that the algorithm container is able to reach.

VPN connection
^^^^^^^^^^^^^^

Algorithm containers can expose one or more ports. These ports can then
be used by other algorithm containers to exchange data. The
infrastructure uses the Dockerfile from which the algorithm has been
build to determine to which ports are used by the algorithm. This is
done by using the ``EXPOSE`` and ``LABEL`` directives.

For example when an algorithm uses two ports, one port for communication
``com`` and one port for data exchange ``data``. The following block
should be added to you algorithm Dockerfile:

.. code:: docker

   # port 8888 is used by the algorithm for communication purposes
   EXPOSE 8888
   LABEL p8888 = "com"

   # port 8889 is used by the algorithm for data-exchange
   EXPOSE 8889
   LABEL p8889 = "data"

Port ``8888`` and ``8889`` are the internal ports to which the algorithm
container listens. When another container want to communicate with this
container it can retrieve the IP and external port from the central
server by using the ``result_id`` and the label of the port you want to
use (``com`` or ``data`` in this case)


Cross language
--------------

Because algorithms are exchanged through Docker images they can be
written in any language. This is an advantage as developers can use
their preferred language for the problem they need to solve.

.. warning::
    The `wrappers <wrappers.md>`_ are only available for R and Python, so when
    you use different language you need to handle the IO yourself. Consult the
    `Input & Output`_ section on what the node supplies to your algorithm
    container.

When data is exchanged between the user and the algorithm they both need
to be able to read the data. When the algorithm uses a language specific
serialization (e.g. a ``pickle`` in the case of Python or ``RData`` in
the case of R) the user needs to use the same language to read the
results. A better solution would be to use a type of serialization that
is not specific to a language. For our wrappers we use JSON for this
purpose.

.. note::
    Communication between algorithm containers can use language specific
    serialization as long as the different parts of the algorithm use the same
    language.

Package & distribute
--------------------

Once the algorithm is completed it needs to be packaged and made
available for retrieval by the nodes. The algorithm is packaged in a
Docker image. A Docker image is created from a Dockerfile, which acts as
blue-print. Once the Docker image is created it needs to be uploaded to
a registry so that nodes can retrieve it.

Dockerfile
^^^^^^^^^^

A minimal Dockerfile should include a base image, injecting your algorithm and
execution command of your algorithm. Here are several examples:

.. raw:: html

   <details>
   <summary><a>Example Dockerfile</a></summary>


.. code:: docker

   # python3 image as base
   FROM python:3

   # copy your algorithm in the container
   COPY . /app

   # maybe your algorithm is installable.
   RUN pip install /app

   # execute your application
   CMD python /app/app.py

.. raw:: html

   </details>
   <br/>


.. raw:: html

   <details>
   <summary><a>Example Dockerfile with Python wrapper</a></summary>

When using the Python `Wrappers`_, the Dockerfile needs to follow a certain
format. You should only change the ``PKG_NAME`` value to the Python
package name of your algorithm.

.. code:: docker

   # python vantage6 algorithm base image
   FROM harbor.vantage6.ai/algorithms/algorithm-base

   # this should reflect the python package name
   ARG PKG_NAME="v6-summary-py"

   # install federated algorithm
   COPY . /app
   RUN pip install /app

   ENV PKG_NAME=${PKG_NAME}

   # Tell docker to execute `docker_wrapper()` when the image is run.
   CMD python -c "from vantage6.tools.docker_wrapper import docker_wrapper; docker_wrapper('${PKG_NAME}'

.. note::
    When using the python wrapper your algorithm file needs to be installable. See
    `here <https://packaging.python.org/en/latest/tutorials/packaging-projects/>`_ for
    more information on how to create a python package.

.. raw:: html

   </details>
   <br/>

.. raw:: html

   <details>
   <summary><a>Example Dockerfile with R wrapper</a></summary>

When using the R `Wrappers`_, the Dockerfile needs to follow a certain format.
You should only change the ``PKG_NAME`` value to the R package name of your
algorithm.

.. code:: docker

   # The Dockerfile tells Docker how to construct the image with your algorithm.
   # Once pushed to a repository, images can be downloaded and executed by the
   # network hubs.
   FROM harbor2.vantage6.ai/base/custom-r-base

   # this should reflect the R package name
   ARG PKG_NAME='vtg.package'

   LABEL maintainer="Main Tainer <m.tainer@vantage6.ai>"

   # Install federated glm package
   COPY . /usr/local/R/${PKG_NAME}/

   WORKDIR /usr/local/R/${PKG_NAME}
   RUN Rscript -e 'library(devtools)' -e 'install_deps(".")'
   RUN R CMD INSTALL --no-multiarch --with-keep.source .

   # Tell docker to execute `docker.wrapper()` when the image is run.
   ENV PKG_NAME=${PKG_NAME}
   CMD Rscript -e "vtg::docker.wrapper('$PKG_NAME')"

.. raw:: html

   </details>

.. note::
    Additional Docker directives are needed when using direct communication
    between different algorithm containers, see `Networking`_.

Build & upload
^^^^^^^^^^^^^^

If you are in the folder containing the Dockerfile, you can build the
project as follows:

::

   docker build -t repo/image:tag .

The ``-t`` indicated the name of your image. This name is also used as
reference where the image is located on the internet. If you use Docker
hub to store your images, you only specify your username as ``repo``
followed by your image name and tag: ``USERNAME/IMAGE_NAME:IMAGE_TAG``.
When using a private registry ``repo`` should contain the URL of the
registry also: e.g. ``harbor2.vantage6.ai/PROJECT/IMAGE_NAME:TAG``.

Then you can push you image:

::

   docker push repo/image:tag

Now that is has been uploaded it is available for nodes to retrieve when
they need it.

Signed images
^^^^^^^^^^^^^

It is possible to use the Docker the framework to create signed images.
When using signed images, the node can verify the author of the algorithm
image adding an additional protection layer.

.. todo
    The part below is rather vague

Dockerfile

-  Build project
-  CMD
-  Expose

.. todo
    Harbor or Docker hub or whatever
    public vs private
    signed

