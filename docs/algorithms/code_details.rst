.. _algo-code_structure:

Algorithm code structure
========================

.. note::

  These guidelines are Python specific.

Here we provide some more information on algorithm code is organized.
Most of these structures are generated automatically when you create a
:ref:`personalized algorithm starting point <algo-dev-create-algorithm>`. We detail
them here so that you understand why the algorithm code is structured as it is,
and so that you know how to modify it if necessary.

Defining functions
------------------

The functions that will be available to the user have to be defined in the
``__init__.py`` file at the base of your algorithm module. Other than that,
you have complete freedom in which functions you implement.

Vantage6 algorithms commonly have an orchestator or aggregator part and a
remote part. The orchestrator part is responsible for combining the partial
results of the remote parts. The remote part is usually executed at each of the
nodes included in the analysis. While this structure is common for vantage6
algorithms, it is not required.

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

.. _implementing-decorators:

Implementing the algorithm functions
------------------------------------

Let's say you are implementing a function called ``my_function``:

.. code:: python

   def my_function(column_name: str):
       pass

You have complete freedom as to what arguments you define in your function;
``column_name`` is just an example. Note that these arguments
have to be provided by the user when the algorithm is called. This is explained
:ref:`here <pyclient-create-task>` for the Python client.

Often, you will want to use the data that is available at the node. This data
can be provided to your algorithm function in the following way:

.. code:: python

    import pandas as pd
    from vantage6.algorithm.tools.decorators import data

    @data(2)
    def my_function(df1: pd.DataFrame, df2: pd.DataFrame, column_name: str):
        pass

The ``@data(2)`` decorator indicates that the first two arguments of the
function are dataframes that should be provided by the vantage6 infrastructure.
In this case, the user would have to specify two databases when calling the
algorithm. Note that depending on the type of the database used, the user may
also have to specify additional parameters such as a SQL query or the name of a
worksheet in an Excel file.

Note that it is also possible to just specify ``@data()`` without an argument -
in that case, a single dataframe is added to the arguments.

For some data sources it's not trivial to construct a dataframe from the data.
One of these data sources is the OHDSI OMOP CDM database. For this data source,
the ``@database_connection`` is available:

.. code:: python

    from rpy2.robjects import RS4
    from vantage6.algorithm.tools.decorators import (
        database_connection, OHDSIMetaData
    )

    @database_connection(types=["OMOP"], include_metadata=True)
    def my_function(connection: RS4, metadata: OHDSIMetaData,
                    <other_arguments>):
        pass

This decorator provides the algorithm with a database connection that can be
used to interact with the database. For instance, you can use this connection
to execute functions from
`python-ohdsi <https://python-ohdsi.readthedocs.io/>`_ package. The
``include_metadata`` argument indicates whether the metadata of the database
should also be provided. It is possible to connect to multiple databases at
once, but you can also specify a single database by using the ``types``
argument.

.. code:: python

    from rpy2.robjects import RS4
    from vantage6.algorithm.tools.decorators import database_connection

    @database_connection(types=["OMOP", "OMOP"], include_metadata=False)
    def my_function(connection1: RS4, connection2: Connection,
                    <other_arguments>):
        pass

.. note::

    The ``@database_connection`` decorator is current only available for
    OMOP CDM databases. The connection object ``RS4`` is an R object, mapped
    to Python using the `rpy2 <https://rpy2.github.io/>`_, package. This
    object can be passed directly on to the functions from
    `python-ohdsi <https://python-ohdsi.readthedocs.io/>`.

Another useful decorator is the ``@algorithm_client`` decorator:

.. code:: python

    import pandas as pd
    from vantage6.client.algorithm_client import AlgorithmClient
    from vantage6.algorithm.tools.decorators import algorithm_client, data

    @data()
    @algorithm_client
    def my_function(client: AlgorithmClient, df1: pd.DataFrame, column_name: str):
        pass

This decorator provides the algorithm with a client that can be used to interact
with the vantage6 central server. For instance, you can use this client in
the central part of an algorithm to create a subtasks for each node with
``client.task.create()``. A full list of all commands that are available
can be found in the :ref:`algorithm client documentation <algo-client-api-ref>`.

.. warning::

    The decorators ``@data`` and ``@algorithm_client`` each have one reserved
    keyword: ``mock_data`` for the ``@data`` decorator and ``mock_client`` for
    the ``@algorithm_client`` decorator. These keywords should not be used as
    argument names in your algorithm functions.

    The reserved keywords are used by the
    :ref:`MockAlgorithmClient <mock-test-algo-dev>` to mock the data and the
    algorithm client. This is useful for testing your algorithm locally.


Algorithm wrappers
------------------

The vantage6 :ref:`wrappers <wrapper-concepts>` are used to simplify the
interaction between the algorithm and the node. The wrappers are responsible
for reading the input data from the data source and supplying it to the algorithm.
They also take care of writing the results back to the data source.

As algorithm developer, you do not have to worry about the wrappers. The only
thing you have to make sure is that the following line is present at the end of
your ``Dockerfile``:

.. code:: docker

    CMD python -c "from vantage6.algorithm.tools.wrap import wrap_algorithm; wrap_algorithm()"

The ``wrap_algorithm`` function will wrap your algorithm to ensure that the
vantage6 algorithm tools are available to it.

For R, the command is slightly different:

.. code:: r

   CMD Rscript -e "vtg::docker.wrapper('$PKG_NAME')"

Also, note that when using R, this only works for CSV files.

.. _vpn-in-algo-dev:

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
different parts of your algorithm), you can do so by adding lines to the
Dockerfile:

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


Dockerfile structure
--------------------

Once the algorithm code is written, the algorithm needs to be packaged and made
available for retrieval by the nodes. The algorithm is packaged in a Docker
image. A Docker image is created from a Dockerfile, which acts as a blue-print.

The Dockerfile is already present in the boilerplate code. Usually, the only
line that you need to update is the ``PKG_NAME`` variable to the name of your
algorithm package.

