.. _algo-code_structure:

Algorithm code structure
========================

.. note::

  This information is specific to Python algorithms.

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

You may also define algorithm functions to extract data from the node data sources,
or to preprocess data that has been extracted. The most common order of execution is to:

1. Create a session
2. Extract data from the node data sources into one (or more) dataframes
3. Preprocess the dataframes
4. Run the analyses

By doing this, you ensure that your analyses are all run on the same data, and it saves
time in extracting data from the node data sources once instead of once per analysis.
More information about sessions can be found in the :ref:`algo-sessions` section.

If you do follow this structure however, we recommend the following file
structure:

.. code:: bash

   my_algorithm/
   ├── __init__.py
   ├── central.py
   └── partial.py
   └── preprocessing.py
   └── extraction.py

where ``__init__.py`` contains something like the following:

.. code:: python

   from .central import my_central_function
   from .partial import my_partial_function1, my_partial_function2
   from .preprocessing import my_preprocessing_function
   from .extraction import my_data_extraction_function

The other files obviously contain the implementation of those functions. You may create
as many files and functions as you wish, but note that only functions that are
imported in ``__init__.py`` will be available to the vantage6 user.

.. _implementing-decorators:

Implementing the algorithm functions
------------------------------------

Let's say you are implementing a function called ``my_function``:

.. code:: python

   def my_function(column_name: str):
       pass

You have complete freedom as to what arguments you define in your function -
``column_name`` is just an example. These arguments have to be provided by the user when
the algorithm is called. The only restriction to the arguments is that they must be
JSON serializable. This is because vantage6 uses JSON to pass arguments to the
algorithm. How a user can provide the arguments is explained
:ref:`here <pyclient-create-task>` for the Python client. In the user interface, a user
can provide the arguments by filling in a form.

In many functions you implement, you will want to use the data that is available at the
node. This data can be provided to your algorithm function in the following way:

.. code:: python

    import pandas as pd
    from vantage6.algorithm.decorator import dataframe

    @dataframe(2)
    def my_function(df1: pd.DataFrame, df2: pd.DataFrame, column_name: str):
        pass

The ``@dataframe(2)`` decorator indicates that the first two arguments of the
function are dataframes that are provided by the vantage6 infrastructure.
In this case, the user will have to specify two dataframes when calling the
algorithm.

Another useful decorator is the ``@algorithm_client`` decorator:

.. code:: python

    import pandas as pd
    from vantage6.client.algorithm_client import AlgorithmClient
    from vantage6.algorithm.decorator.algorithm_client import algorithm_client
    from vantage6.algorithm.decorator.data import dataframe

    @dataframe(1)
    @algorithm_client
    def my_function(client: AlgorithmClient, df1: pd.DataFrame, column_name: str):
        pass

This decorator provides the algorithm with a client that can be used to interact
with the vantage6 central server. For instance, you can use this client in
the central part of an algorithm to create a subtasks for each node with
``client.task.create()``. A full list of all commands that are available
can be found in the :ref:`algorithm client documentation <algo-client-api-ref>`.

.. warning::

    The decorators ``@dataframe``,  ``@algorithm_client`` and ``@database_connection``
    each have reserved keywords:

    - ``mock_data`` for the ``@dataframe`` decorator
    - ``mock_client`` for the ``@algorithm_client`` decorator
    - ``mock_uri`` and ``mock_type`` for the ``@database_connection`` decorator

    These keywords should not be used as argument names in your algorithm functions.
    The reserved keywords are used by the :ref:`MockNetwork <mock-test-algo-dev>` to
    mock the data and the algorithm client. This is useful for testing your algorithm
    locally.

Advanced decorators
------------------

A useful decorator for computation tasks is the ``@metadata`` decorator:

.. code:: python

    from vantage6.algorithm.decorator.metadata import (metadata, RunMetaData)


    @metadata
    def my_function(metadata: RunMetaData, <other_arguments>):
        # The metadata contains a dataclass with the following attributes:
        # task_id, node_id, collaboration_id, organization_id, temporary_directory,
        # output_file, input_file, token, action.
        #
        # They can be easily accessed using the dot notation. For example:
        return metadata.task_id

For some data sources it's not trivial to construct a dataframe from the data.
One of these data sources is the OHDSI OMOP CDM database. For this data source,
the ``@omop_data_extraction`` is available:

.. code:: python

    from rpy2.robjects import RS4
    from vantage6.algorithm.decorators import omop_data_extraction
    from vantage6.algorithm.decorator.ohdsi import OHDSIMetaData

    @omop_data_extraction(include_metadata=True)
    def my_function(connection: RS4, metadata: OHDSIMetaData,
                    <other_arguments>):
        pass

This decorator provides the algorithm with a database connection that can be
used to interact with the database. For instance, you can use this connection
to execute functions from
`python-ohdsi <https://python-ohdsi.readthedocs.io/>`_ package. The
``include_metadata`` argument indicates whether the metadata of the database
should also be provided.

.. note::

    The returned ``connection object`` (``RS4``) is an R object, mapped
    to Python using the `rpy2 <https://rpy2.github.io/>`_, package. This
    object can be passed directly on to the functions from
    `python-ohdsi <https://python-ohdsi.readthedocs.io/>`.

Another useful decorator is the ``@algorithm_client`` decorator:

.. code:: python

    import pandas as pd
    from vantage6.client.algorithm_client import AlgorithmClient
    from vantage6.algorithm.decorator.algorithm_client import algorithm_client
    from vantage6.algorithm.decorator.data import dataframe

    @dataframe(1)
    @algorithm_client
    def my_function(client: AlgorithmClient, df1: pd.DataFrame, column_name: str):
        pass

This decorator provides the algorithm with a client that can be used to interact
with the vantage6 central server. For instance, you can use this client in
the central part of an algorithm to create a subtasks for each node with
``client.task.create()``. A full list of all commands that are available
can be found in the :ref:`algorithm client documentation <algo-client-api-ref>`.

.. warning::

    The decorators ``@dataframe``, ``@database_connection`` and ``@algorithm_client``
    each have reserved keywords:
    - ``mock_data`` for the ``@dataframe`` decorator
    - ``mock_client`` for the ``@algorithm_client`` decorator
    - ``mock_uri`` and ``mock_type`` for the ``@database_connection`` decorator
    These keywords should not be used as argument names in your algorithm functions.

    The reserved keywords are used by the :ref:`MockNetwork <mock-test-algo-dev>` to
    mock the data and the algorithm client. This is useful for testing your algorithm
    locally.


Algorithm wrappers
------------------

The vantage6 :ref:`wrappers <wrapper-concepts>` are used to simplify the
interaction between the algorithm and the node. The wrappers are responsible
for translating user input to call the right algorithm method with the right arguments.
They also take care of writing the results back to the data source.

As algorithm developer, you do not have to worry about the wrappers. The main
point you have to make sure is that the following line is present at the end of
your ``Dockerfile``:

.. code:: docker

    CMD python -c "from vantage6.algorithm.tools.wrap import wrap_algorithm; wrap_algorithm()"

The ``wrap_algorithm`` function will wrap your algorithm to ensure that the
vantage6 algorithm tools are available to it. Note that the ``wrap_algorithm``
function will also read the ``PKG_NAME`` environment variable from the
``Dockerfile`` so make sure that this variable is set correctly.

Dockerfile structure
--------------------

Once the algorithm code is written, the algorithm needs to be packaged and made
available for retrieval by the nodes. The algorithm is packaged in a Docker
image. A Docker image is created from a Dockerfile, which acts as a blue-print.

The Dockerfile is already present in the boilerplate code. Usually, the only
line that you need to update is the ``PKG_NAME`` variable to the name of your
algorithm package.
