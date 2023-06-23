Algorithm development guide
===========================

This page offers a step-by-step guide to develop your own vantage6 algorithms.
In doing so, we refer to the `algorithm concepts <algo-concepts>`_ section
regularly. In that section, we explain the fundamentals of algorithm containers
in more detail than in this guide.

Also, note that this guide is mainly aimed at developers who want to develop
their algorithm in Python, although we will try to clearly indicate where
this differs from algorithms written in other languages.

Starting point
--------------

The easiest way to start creating an algorithm is to have a template to start
from. You can find such a template in the Github repository
`v6-boilerplate <https://github.com/IKNL/v6-boilerplate-py>`_. So start with

.. code:: bash

   git clone https://github.com/IKNL/v6-boilerplate-py

and you are ready to start!

Note that there are also several algorithms that have been written in R, such
as `vtg.basic <https://github.com/IKNL/vtg.basic>`_. If you plan to write your
algorithm in R, you can use this as a starting point.

.. note::

    We are working on a more flexible template based on
    `Cookiecutter <https://github.com/cookiecutter/cookiecutter>`_. When this
    is ready, a personalized template will be created for you after you answer
    a few questions.

Deciding which functions to implement
-------------------------------------

The functions that will be available to the user have to be defined in the
``__init__.py`` file at the base of your algorithm module. Other than that,
you have complete freedom in which functions you implement.

Often, vantage6 algorithms consists of two parts: a central part and a
partial or federated part. The partial or federated part is the
part that is executed at each the nodes that participates in an analysis.
The central part is responsible for orchestrating the algorithm and combining
the partial results. However, this structure is not a requirement.

If you do follow this structure however, we recommend the following file
structure:

.. code:: bash

   my_algorithm/
   ├── __init__.py
   ├── central.py
   └── partial.py

where ``__init__.py`` contains the following:

.. code:: python

   from .central import my_central_function
   from .partial import my_partial_function

and where ``central.py`` and ``partial.py`` obviously contain the implementation
of those functions.

Implementing the algorithm functions
------------------------------------

Let's say you are implementing a function called ``my_function``:

.. code:: python

   def my_function(column_name: str):
       pass

Now, you have a lot of freedom as to what arguments you define in your function.
In this case ``column_name`` is just an example. Note that these arguments
have to be provided by the user when the algorithm is called. This is explained
:ref:`here <pyclient-create-task>` for the Python client.

Often, you will want to use the data that is available at the node. This data
can be provided to your algorithm function in the following way:

.. code:: python

    import pandas as pd

    @data(2)
    def my_function(df1: pd.DataFrame, df2: pd.DataFrame, column_name: str):
        pass

The ``@data(2)`` decorator indicates that the first two arguments of the
function are dataframes that are provided by the vantage6 infrastructure.
In this case, the user would have to specify two databases when calling the
algorithm. Note that the user should also specify the data type of the database
and optionally, additional parameters such as a SQL query or the name of a
worksheet in an Excel file.

Note that it is also possible to just specify ``@data()`` without an argument -
in that case, a single dataframe is added to the arguments.

A second decorator that is often used is the ``@algorithm_client`` decorator:

.. code:: python

    import pandas as pd
    from vantage6.client.algorithm_client import AlgorithmClient

    @data()
    @algorithm_client
    def my_function(client: AlgorithmClient, df1: pd.DataFrame, column_name: str):
        pass

This decorator provides the algorithm with a client that can be used to interact
with the vantage6 central server. For instance, you can use this client in
the central part of an algorithm to create a subtasks for each node with
``client.task.create()``. A full list of all commands that are available
can be found in the :ref:`algorithm client documentation <algo-client-api-ref>`.

Algorithm wrappers
----------------

The vantage6 :ref:`wrappers <wrapper-concepts>` are used to simplify the
interaction between the algorithm and the node. The wrappers are responsible
for reading the input data from the data source and supplying it to the algorithm.
They also take care of writing the results back to the data source.

As algorithm developer, you do not have to worry about the wrappers. The only
thing you have to make sure is that the following line is present at the end of
your ``Dockerfile``:

.. code:: docker

    CMD python -c "from vantage6.tools.wrap import wrap_algorithm; wrap_algorithm('${PKG_NAME}')"

where ``${PKG_NAME}`` is the name of your algorithm package. The ``wrap_algorithm``
function will wrap your algorithm.

Environment variables
---------------------

The algorithms have access to several environment variables. These can be used
to locate certain files or to add local configuration settings into the
container.

There are several environment variables that are always available. These are
listed in the :ref:`table-env-vars` table. In addition, environment variables can be
added to the container by specifying them using the ``algorithm_env`` option
in the node configuration file (see the :ref:`example node configuration file <node-configure-structure>`).

.. _table-env-vars:

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

VPN
---

Within vantage6, it is possible to communicate with algorithm instances running
on different nodes via the :ref:`VPN network feature <vpn-feature>`. Each of
the algorithm instances has their own IP address and port within the VPN
network. In your algorithm code, you can use the ``AlgorithmClient`` to obtain
the IP address and port of other algorithm instances. For example:

.. code:: python

    from vantage6.client import AlgorithmClient

    def my_function(client: AlgorithmClient, ...):
        # Get the IP address and port of the algorithm instance with id 1
        child_addresses = client.get_child_addresses()
        # returns something like:
        # [
        #     {
        #       'port': 1234,
        #       'ip': 11.22.33.44,
        #       'label': 'some_label',
        #       'organization_id': 22,
        #       'task_id': 333,
        #       'parent_id': 332,
        #     }, ...
        # ]

        # Do something with the IP address and port

The function ``get_child_addresses()`` gets the VPN addresses of all child
tasks of the current task. Similarly, the function ``get_parent_address()``
is available to get the VPN address of the parent task. Finally, there is
a client function ``get_addresses()`` that returns the VPN addresses of all
algorithm instances that are part of the same task.

VPN communication is only possible if the docker container exposes ports to
the VPN network. In the algorithm boilerplate, one port is exposed by default.
If you need to expose more ports (e.g. for sending different information to
different parts of your algorithm), you can do so by adding the lines such as
the following to the Dockerfile:

.. code:: bash

   # port 8888 is used by the algorithm for communication purposes
   EXPOSE 8888
   LABEL p8888 = "some-label"

   # port 8889 is used by the algorithm for data-exchange
   EXPOSE 8889
   LABEL p8889 = "some-other-label"

The ``EXPOSE`` command exposes the port to the VPN network. The ``LABEL``
command adds a label to the port. This label returned with the clients'
``get_addresses()`` function suite. You may specify as many ports as you need.
Note that you *must* specify the label with ``p`` as prefix followed by the
port number. The vantage6 infrastructure relies on this naming convention.

Returning results
-----------------

Returning the results of you algorithm is rather straightforward. At the end
of your algorithm function, you can simply return the results as a dictionary:

.. code:: python

    def my_function(column_name: str):
        return {
            "result": 42
        }

These results will be returned to the user after the algorithm has finished.

.. warning::

    The results that you return should be JSON serializable. This means that
    you cannot, for example, return a ``pandas.DataFrame`` or a
    ``numpy.ndarray``. Such objects should be converted to a JSON serializable
    format first.

Testing your algorithm
----------------------

.. TODO MockClient stuff

Writing documentation
---------------------

It is important that you add documentation of your algorithm so that users
know how to use it. In principle, you may choose any format of documentation,
and you may choose to host it anywhere you like. However, we recommend to
keep your documentation close to the code, for instance in the ``README.md``
file. Alternatively, we recommend using the ``readthedocs`` platform to host
your documentation.

.. note::

    In the near future, we will provide a template for the documentation of
    algorithms with the boilerplate. This template will be based on the
    ``readthedocs`` platform.

Modifying the Dockerfile
------------------------

Once the algorithm code is written, the algorithm needs to be packaged and made
available for retrieval by the nodes. The algorithm is packaged in a Docker
image. A Docker image is created from a Dockerfile, which acts as a blue-print.

The Dockerfile is already present in the boilerplate code. Usually, you do not
need to change many things in the Dockerfile. However, you should make sure
to update the ``PKG_NAME`` variable to the name of your algorithm package.


Package & distribute
--------------------

If you are in the folder containing the Dockerfile, you can build the
project as follows:

.. code:: bash

   docker build -t repo/image:tag .

The ``-t`` indicated the name of your image. This name is also used as
reference where the image is located on the internet. Once the Docker image is
created it needs to be uploaded to a registry so that nodes can retrieve it,
which you can do by pushing the image:

.. code:: bash

   docker push repo/image:tag

Here are a few examples of how to build and upload your image:

.. code:: bash

    # Build and upload to Docker Hub. Replace <my-user-name> with your Docker
    # Hub username and make sure you are logged in with ``docker login``.
    docker build -t my-user-name/algorithm-example:latest .
    docker push my-user-name/algorithm-example:latest

    # Build and upload to private registry. Here you don't need to provide
    # a username but you should write out the full image URL. Also, again you
    # need to be logged in with ``docker login``.
    docker build -t harbor2.vantage6.ai/PROJECT/algorithm-example:latest .
    docker push harbor2.vantage6.ai/PROJECT/algorithm-example:latest

Now that your algorithm has been uploaded it is available for nodes to retrieve
when they need it.

Calling your algorithm from vantage6
------------------------------------

If you want to test your algorithm in the context of vantage6, you should
set up a vantage6 infrastructure. You should create a server and at least one
node (depending on your algorithm you may need more). Follow the instructions
in the :ref:`server-admin-guide` and :ref:`node-admin-guide` to set up your
infrastructure. If you are running them on the same machine, take care to
provide the node with the proper address of the server as detailed
:ref:`here <use-server-local>`.

Once your infrastructure is set up, you can create a task for your algorithm.
You can do this either via the :ref:`UI <ui>` or via the
:ref:`Python client <pyclient-create-task>`.