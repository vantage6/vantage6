.. _algo-dev-guide:

Algorithm development step-by-step guide
========================================

This page offers a step-by-step guide to develop a vantage6 algorithm.
We refer to the `algorithm concepts <algo-concepts>`_ section
regularly. In that section, we explain the fundamentals of algorithm containers
in more detail than in this guide.

Also, note that this guide is mainly aimed at developers who want to develop
their algorithm in Python, although we will try to clearly indicate where
this differs from algorithms written in other languages.

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

.. note::
   There is also a `boilerplate for R <https://github.com/IKNL/vtg.tpl>`_,
   but this is not flexible and it is not updated as frequently as the Python
   boilerplate.

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
   conda create -n <my-algorithm-env> python=3.10
   conda activate <my-algorithm-env>

   # install the algorithm dependencies
   pip install -r requirements.txt

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

.. _algo-env-vars:

Environment variables
---------------------

The algorithms have access to several environment variables. You can also
specify additional environment variables via the ``algorithm_env`` option
in the node configuration files (see the
:ref:`example node configuration file <node-configure-structure>`).

Environment variables provided by the vantage6 infrastructure are used
to locate certain files or to add local configuration settings into the
container. These are usually used in the Python wrapper and you don't normally
need them in your functions. However, you can access them in your functions
as follows:

.. code:: python

   def my_function():
       # environment variable that specifies the input file
       input_file = os.environ["INPUT_FILE"]
       # environment variable that specifies the database URI for the database with
       # the 'default' label
       default_database_uri = os.environ["DEFAULT_DATABASE_URI"]

       # do something with the input file and database URI
       pass

The environment variables that you specify in the node configuration file
can be used in the exact same manner. You can view all environment variables
that are available to your algorithm by ``print(os.environ)``.

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
    ``numpy.ndarray`` (such objects may not be readable to a non-Python using
    recipient or may even be insecure to send over the internet). They should
    be converted to a JSON-serializable format first.

Example functions
-----------------

Just an example of how you can implement your algorithm:

Central function
~~~~~~~~~~~~~~~~

.. code:: python

  from vantage6.algorithm.tools.decorators import algorithm_client
  from vantage6.algorithm.client import AlgorithmClient
  # info and error can be used to log algorithm events
  from vantage6.algorithm.tools.util import info, error

   @algorithm_client
   def main(client: AlgorithmClient, *args, **kwargs):
      # Run partial function.
      task = client.task.create(
         method="my_partial_function",
         input_={
            # Method name should match the name of the partial function used/created
            "args": args,
            "kwargs": kwargs
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
   from vantage6.algorithm.tools.decorator import data

   @data(1)
   def my_partial_function(data: pd.DataFrame, column_name: str):
       # do something with the data
       data[column_name] = data[column_name] + 1

       # return the results
       return {
           "result": sum(data[colum_name].to_list())
       }

.. _mock-test-algo-dev:

Testing your algorithm
----------------------

It can be helpful to test your algorithm outside of Docker using the
``MockAlgorithmClient``. This may save
time as it does not require you to set up a test infrastructure with a vantage6
server and nodes, and allows you to test your algorithm without building a
Docker image every time. The algorithm boilerplate code comes with a test file that
you can use to test your algorithm using the ``MockAlgorithmClient`` - you can
of course extend that to add more or different tests.

The :ref:`MockAlgorithmClient <mock-client-api-ref>` has the same interface as
the ``AlgorithmClient``, so it should be easy to switch between the two. An
example of how you can use the ``MockAlgorithmClient`` to test your algorithm
is included in the boilerplate code.

Writing documentation
---------------------

It is important that you add documentation of your algorithm so that users
know how to use it. In principle, you may choose any format of documentation,
and you may choose to host it anywhere you like. However, in our experience it
works well to keep your documentation close to your code. We recommend using the
``readthedocs`` platform to host your documentation. Alternatively, you could
use a ``README`` file in the root of your algorithm directory - if the
documentation is not too extensive, this may be sufficient.

.. note::

    We intend to provide a template for the documentation of algorithms in the
    future. This template will be based on the ``readthedocs`` platform.

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
set up a vantage6 infrastructure. You should create a server and at least one
node (depending on your algorithm you may need more). Follow the instructions
in the :ref:`server-admin-guide` and :ref:`node-admin-guide` to set up your
infrastructure. If you are running them on the same machine, take care to
provide the node with the proper address of the server as detailed
:ref:`here <use-server-local>`.

Once your infrastructure is set up, you can create a task for your algorithm.
You can do this either via the :ref:`UI <ui>` or via the
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
        client = Client("http://localhost", Ports.DEV_SERVER.value, "/api")
        client.authenticate("dev_admin", "password")

        input_ = {
            "method": "central_average",
            "args": [],
            "kwargs": {"column_name": "Age"},
        }

        # create the task
        task = client.task.create(
            collaboration=1,
            organizations=[1],
            name="test_average_task",
            image="harbor2.vantage6.ai/demo/average",
            description="",
            input_=input_,
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

   v6 test client-script --task-arguments "{ 'collaboration': 1, 'organizations': [1], 'name': 'task_name', 'image': 'my_image', 'description': '', 'input_': { 'method': 'my_method', 'args': [], 'kwargs': {'column_name': 'my_column'}}, 'databases': [{'label': 'db_label'}]}"

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
