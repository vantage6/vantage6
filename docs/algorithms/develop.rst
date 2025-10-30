.. _algo-dev-guide:

Algorithm development step-by-step guide
========================================

This page offers a step-by-step guide to develop a vantage6 algorithm.
We refer to the `algorithm concepts <algo-concepts>`_ section
regularly. In that section, we explain the fundamentals of algorithm containers
in more detail than in this guide.

Also, note that this guide is mainly aimed at developers who want to develop
their algorithm in Python, although we will try to clearly indicate where
this differs from algorithms written in other languages. Writing your algorithm in
Python is recommended because it is currently the best supported  language for vantage6.

.. _algo-dev-create-algorithm:

Starting point
--------------

When starting to develop a new vantage6 algorithm in Python, the easiest way to
start is:

.. code::

   v6 algorithm create

Running this command will prompt you to answering some questions, which will
result in a personalized starting point or 'boilerplate' for your algorithm.
After doing so, you will have a new folder with the name of your algorithm,
boilerplate code and a checklist in the README.md file that you can follow to
complete your algorithm.

Setting up your environment
---------------------------

It is good practice to set up a virtual environment for your algorithm
package.

.. code:: bash

   # This code is just a suggestion - there are many ways of doing this.

   # go to the algorithm directory
   cd /path/to/algorithm

   # create a Python environment. Be sure to replace <my-algorithm-env> with
   # the name of your environment.
   uv venv --python 3.13
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate

   # install the algorithm dependencies
   uv sync

Also, it is always good to use a version control system such as ``git`` to
keep track of your changes. An initial commit of the boilerplate code could be:

.. code:: bash

   cd /path/to/algorithm
   git init
   git add .
   git commit -m "Initial commit"

Note that having your code in a git repository is necessary if you want to
:ref:`update your algorithm <algo-dev-update-algo>`.

Implementing your algorithm
---------------------------

Your personalized starting point should make clear to you which functions you need to
implement - there are `TODO` comments in the code that indicate where you need
to add your own code.

You may wonder why the boilerplate code is structured the way it is. This
is explained in the :ref:`code structure section <algo-code_structure>`.

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
    ``numpy.ndarray``. Such objects may not be readable to a non-Python-using
    recipient, or may even be insecure to send over the internet. They should
    be converted to a JSON-serializable format first (e.g. with ``df.to_json()`` in
    pandas).

.. _algo-env-vars:

Environment variables
---------------------

The algorithms have access to several environment variables. You can also
specify additional environment variables via the ``algorithm_env`` option
in the node configuration files (see the
:ref:`example node configuration file <node-configure-structure>`). You can access
environment variables in your functions as follows:

.. code:: python

   import os

   def my_function():
       # environment variable that specifies the input file
       env_var = os.environ["ENV_VAR_SPECIFIED_IN_NODE_CONFIG"]

       # do something with the input file and database URI
       pass

You can view all environment variables that are available to your algorithm by
``print(os.environ)``. This includes a number of environment variables that are
provided by the vantage6 infrastructure.

Example functions
-----------------

Just an example of how you can implement your algorithm:

Central function
~~~~~~~~~~~~~~~~

.. code:: python

  from vantage6.algorithm.decorator.algorithm_client import algorithm_client
  from vantage6.algorithm.client import AlgorithmClient
  from vantage6.algorithm.tools.util import info, error

   @algorithm_client
   def main(client: AlgorithmClient, *args, **kwargs):
      # Run partial function.
      info("Creating subtask for partial function")
      task = client.task.create(
         method="my_partial_function",
         arguments={
            "function_argument_1": "value_1",
            "function_argument_2": "value_2"
         },
         organizations=[1, 2]
      )

       # wait for the federated part to complete
       # and return
       results = client.wait_for_results(task_id=tesk.get("id"))

       return results

Partial function
~~~~~~~~~~~~~~~~

.. code:: python

   import pandas as pd
   from vantage6.algorithm.tools.decorator import dataframe

   @dataframe(1)
   def my_partial_function(data: pd.DataFrame, column_name: str):
       # do something with the data
       data[column_name] = data[column_name] + 1

       # return the results
       return {
           "result": sum(data[colum_name].to_list())
       }

Data extraction function
~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   import os
   import pandas as pd

   from vantage6.algorithm.decorator.action import data_extraction
   from vantage6.algorithm.tools.util import info

   @data_extraction
   def my_data_extraction_function(db_connection_details: dict):
       info("Extracting data")

       # for a CSV database, the URI is the path to the CSV file
       df = pd.read_csv(db_connection_details["uri"])

       # for a SQL database, the URI is the connection string. Environment variables
       # such as username+password can be provided in the node configuration file.
       df = pd.read_sql_query(
         db_connection_details["uri"],
         db_connection_details["query"],
         os.getenv("USERNAME"),
         os.getenv("PASSWORD"),
      )

       return df

Preprocessing function
~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

   import pandas as pd

   from vantage6.algorithm.decorator.action import preprocessing
   from vantage6.algorithm.tools.util import info

   @preprocessing
   def my_preprocessing_function(df: pd.DataFrame):
       # do some preprocessing with the data
       df["column_name"] = df["column_name"] + 1
       return df

Functions provided by the vantage6 infrastructure
-------------------------------------------------

There are already some data extraction and preprocessing functions provided by the
vantage6 infrastructure. These contain the most common data extractions (such as
CSV, Excel, Parquet and basic SQL wrappers) and common preprocessing transformations.

You can make these functions available in your algorithm by importing them from the
vantage6 algorithm tools:

.. code:: python

   # in your algorithm's __init__.py file
   from vantage6.algorithm.data_extraction import *
   from vantage6.algorithm.preprocessing import *

.. note::

   As algorithm developer, you should keep in mind that error messages may contain
   sensitive information. In Python, we often see Pandas errors when manipulating data,
   for instance that a certain data value is not a valid date.

   To help you keep such sensitive information private, vantage6
   provides a decorator that can be used to handle pandas errors. This decorator will
   catch all pandas errors and return a generic error message. You can use this
   decorator by adding it to your algorithm function:

   .. code:: python

      from vantage6.algorithm.tools.error_handling import handle_pandas_errors

      @handle_pandas_errors
      def my_function(data: pd.DataFrame):
         return data

.. _mock-test-algo-dev:

Testing your algorithm
----------------------

It can be helpful to test your algorithm outside of a containerized environment using
the ``MockNetwork``. This may save time as it does not require you to set up a test
infrastructure with a vantage6 server and nodes, and allows you to test your algorithm
without building a Docker image every time. The algorithm boilerplate code comes with a
test file that you can use to test your algorithm using the ``MockNetwork`` - you can
of course extend that to add more or different tests.

The ``MockNetwork`` comes with a ``MockAlgorithmClient`` and a ``MockUserClient`` that
have the same interface as the ``AlgorithmClient`` and the ``UserClient``, so it should
be easy to switch between the two. The following example shows how to use the
``MockUserClient`` to test your algorithm:

.. code:: python

        from vantage6.mock.mock_network import MockNetwork
        network = MockNetwork(
            module_name="my_algorithm",
            datasets=[{"dataset_1": {"database": "mock_data.csv", "db_type": "csv"}}],
        )
        client = network.user_client
        client.dataframe.create(
            label="dataset_1", method="my_method", arguments={}
        )
        client.task.create(
            method="my_method",
            organizations=[0],
            arguments={
                "example_argument": 10
            },
            databases=[{"label": "dataset_1"}]
        )
        results = client.result.from_task(task.get("id"))
        print(results)

Or in case you do not want to test data extraction you can provide a pandas
DataFrame instead of a string for the database value:

.. code:: python

        import pandas as pd
        from vantage6.mock.mock_network import MockNetwork

        network = MockNetwork(
            module_name="my_algorithm",
            datasets=[{"dataset_1": pd.DataFrame({"column_1": [1, 2, 3]})}],
        )
        client = network.user_client
        client.task.create(
            method="my_method",
            organizations=[0],
            arguments={
                "example_argument": 10
            },
            databases=[{"label": "dataset_1"}]
        )
        results = client.result.from_task(task.get("id"))
        print(results)

Writing documentation
---------------------

It is important that you add documentation of your algorithm so that users
know how to use it. In principle, you may choose any format of documentation,
and you may choose to host it anywhere you like. However, in our experience it
works well to keep your documentation close to your code. We recommend using the
``readthedocs`` platform to host your documentation. A template for such documentation
can be generated when running the ``v6 algorithm create`` command.

Alternatively, you could use a ``README`` file - if the documentation is not too
extensive, e.g. the algorithm is onlyfor testing purposes, this may be sufficient.

Package & distribute
--------------------

The algorithm boilerplate comes with a ``Dockerfile`` that is a blueprint for
creating a Docker image of your algorithm. This Docker image is the package
that you will distribute to the nodes.

If you go to the folder containing your algorithm, you will also find the
Dockerfile there, immediately at the top directory. You can then build the
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
set up a vantage6 infrastructure. To do that quickly, you can use the ``v6 sandbox new``
command, which will create a sandbox environment with a server, several nodes and an
algorithm store. Once you have a vantage6 sandbox running, you can create a task for
your algorithm. You can do this either via the :ref:`UI <ui>` or via the
:ref:`Python client <pyclient-create-task>`.

It is also possible to test your algorithm by running a test script on a local
vantage6 :ref:`dev network <create-dev-network>`. This can be done by running
the following CLI command:

.. code:: bash

   v6 test client-script --create-dev-network

This will create a dev network and run the test script included in the repository on the
latest version of the vantage6 infrastructure.
To let the script run the algorithm, the arguments needed by the task should be added to
``algo_test_arguments.py``

A custom test script can be used by running:

.. code:: bash

   v6 test client-script --create-dev-network --script path/to/test_script.py

In this case, the script should contain the code to run and test the algorithm, and return the
execution result. For example, to test the average algorithm, the script could look like this:

.. code:: python

    from vantage6.client import Client
    from vantage6.common.globals import Ports

    def run_test():
        # Create a client and authenticate
        client = Client(
            server_url="http://localhost:7601/server", auth_url="http://localhost:8080"
        )
        client.authenticate()

        # create the task
        task = client.task.create(
            collaboration=1,
            organizations=[1],
            name="test_average_task",
            image="harbor2.vantage6.ai/demo/average",
            description="",
            method="central_average",
            arguments={"column_name": "Age"},
            databases=[{"label": "olympic_athletes"}],
        )

        # wait for the task to complete
        task_result = client.wait_for_results(task["id"])

        # verify the result
        assert task_result.get("data")[0].get("result") == '{"average": 27.613448844884488}'

    if __name__ == "__main__":
        run_test()

Another option to test the algorithm without writing a script, is to pass the arguments
directly to the command:

.. code:: bash

   v6 test client-script --task-arguments "{ 'collaboration': 1, 'organizations': [1], 'name': 'task_name', 'image': 'my_image', 'description': '', 'method': 'my_method', 'arguments': {'column_name': 'my_column'}, 'databases': [{'label': 'db_label'}]}"

After running, the network will be stopped and removed unless you specify otherwise by setting
``--keep true`` in the command.

If a dataset different from the default ones is needed, it can be included in the
dev network by specifying the label and the path to the dataset in the ``--add-dataset``
argument of the command:

.. code:: bash

   v6 test client-script --script /path/to/test_script.py --create-dev-network --add-dataset my_label /path/to/dataset

If a dev network configuration exists, but the network is not running, it is possible
to start the existing network configuration and run the test script on it:

.. code:: bash

   v6 test client-script --script /path/to/test_script.py --start-dev-network --name my_network

If a the ``--start-dev-network`` and the ``--create-dev-network`` arguments are not specified,
the test script will be executed on the running dev network, if active.



.. _algo-dev-update-algo:

Updating your algorithm
-----------------------

At some point, there may be changes in the vantage6 infrastructure that require
you to update your algorithm. Such changes are made available via
the ``v6 algorithm update`` command. This command will update your algorithm
to the latest version of the vantage6 infrastructure.

You can also use the ``v6 algorithm update`` command to update your algorithm
if you want to modify your answers to the questionnaire. In that case, you
should be sure to commit the changes in ``git`` before running the command.
