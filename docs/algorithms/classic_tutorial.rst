.. todo rewrite this to a modern version, taking into account the description
   in the develop.rst file.

.. warning::

    This classic tutorial was written for vantage6 version 2.x. The commands
    below have not been updated and therefore might not work anymore. We are
    leaving this here for reference, as it includes some useful information
    about concepts that may not be included elsewhere in this documentation.

.. _classic-algo-tutorial:

Classic Tutorial
================

In this section the basic steps for creating an algorithm for horizontally
partitioned data are explained.

.. note::
    The final code of this tutorial is published on
    `Github <https://github.com/iknl/v6-average-py>`__. The algorithm is also
    published in our Docker registry: *harbor2.vantage6.ai/demo/average*

It is assumed that it is mathematically possible to create a federated
version of the algorithm you want to use. In the following sections we
create a federated algorithm to compute the average of a distributed
dataset. An overview of the steps that we are going through:

1. Mathematically decompose the model
2. Federated implementation and local testing
3. Vantage6 algorithm wrapper
4. Dockerize and push to a registry

This tutorial shows you how to create a **federated mean** algorithm.

Mathematical decomposition
--------------------------

The mean of :math:`Q = [q_1, q_2 ...  q_n]` is computed as:

.. math::

   Q_{mean} = \frac{1}{n} \sum \limits_{i=1}^{n} {q_i} = \frac{q_1 + q_2 + ... + q_n}{n}

When dataset :math:`Q` is **horizontally partitioned** in dataset :math:`A` and
:math:`B`:

.. math::
    A = [a_1, a_2 ... a_j] = [q_1, q_2 ... q_j]

    B = [b_{1}, b_{2} ... b_k] = [q_{j+1}, q_{j+2}...q_{n}]

We would like to compute :math:`Q_{mean}` from dataset A and B. This could be
computed as:

.. math::

   Q_{mean} = \frac{(a_1+a_2+...+a_j) + (b_1+b_2+...+b_k)}{j+k} = \frac{\sum A
      + \sum B }{j+k}

Both the number of samples in each dataset and the total sum of each
dataset is needed. Then we can compute the global average of dataset :math:`A`
and :math:`B`.

.. note::
    We cannot simply compute the average on each node and combine them, as this
    would be mathematically incorrect. This would only work if dataset **A**
    and **B** contain the exact same number of samples.

Federated implementation
------------------------

.. warning::
    In this example we use python, however you are free to use any language.
    The only requirements are: 1) It has to be able to create HTTP-requests,
    and 2) has to be able to read and write to files.

    However, if you use a different language you are not able to use our
    wrapper. Reach out to us on `Discord <https://discord.gg/yAyFf6Y>`__ to
    discuss how this works.

A federated algorithm consist of two parts:

1. A federated part of the algorithm which is responsible for creating
   the partial results. In our case this would be computing (1) the sum
   of the observations, and (2) the number of observations.
2. A central part of the algorithm which is responsible for combining
   the partial results from the nodes. In the case of the federated mean
   that would be dividing the total sum of the observations by the total
   number of observations.

.. note::
    The central part of the algorithm can either be run on the machine of the
    researcher himself or in a master container which runs on a node. The latter
    is the preferred method.

    In case the researcher runs this part, he/she needs to have a proper
    setup to do so (i.e. a Python environment with the necessary dependencies).
    This can be useful when developing new algorithms.

Federated part
~~~~~~~~~~~~~~

The node that runs this part contains a CSV-file with one column
(specified by the argument *column_name*) which we want to use to
compute the global mean. We assume that this column has no *NaN* values.

.. code:: python

   import pandas

   def federated_part(path, column_name="numbers"):
       """Compute the sum and number of observations of a column"""

       # extract the column numbers from the CSV
       numbers = pandas.read_csv(path)[column_name]

       # compute the sum, and count number of rows
       local_sum = numbers.sum()
       local_count = len(numbers)

       # return the values as a dict
       return {
           "sum": local_sum,
           "count": local_count
       }

Central part
~~~~~~~~~~~~

The central algorithm receives the sums and counts from all sites and
combines these to a global mean. This could be from one or more sites.

.. code:: python

   def central_part(node_outputs):
       """Combine the partial results to a global average"""
       global_sum = 0
       global_count = 0
       for output in node_outputs:
           global_sum += output["sum"]
           global_count += output["count"]

       return {"average": global_sum / global_count}

Local testing
~~~~~~~~~~~~~

To test, simply create two datasets **A** and **B**, both having a
numerical column **numbers**. Then run the following:

.. code:: python

   outputs = [
       federated_part("path/to/dataset/A"),
       federated_part("path/to/dataset/B")
   ]
   Q_average = central_part(outputs)["average"]
   print(f"global average = {Q_average}.")

Vantage6 integration
--------------------

.. note::
    A good starting point would be to use the boilerplate code from our
    `Github <https://github.com/iknl/v6-boilerplate-py>`__. This section
    outlines the steps needed to get to this boilerplate but also provides
    some background information.

.. note::
    In this example we use a **csv**-file. It is also possible to use other
    types of data sources. This tutorial makes use of our algorithm wrapper
    which is currently only available for **csv**, **SPARQL** and **Parquet**
    files.

    Other wrappers like **SQL**, **OMOP**, etc. are under consideration. Let
    us now if you want to use one of these or other datasources.

Now that we have a federated implementation of our algorithm we need to
make it compatible with the vantage6 infrastructure. The infrastructure
handles the communication with the server and provides data access to
the algorithm.

The algorithm consumes a file containing the input. This contains both
the method name to be triggered as well as the arguments provided to the
method. The algorithm also has access to a CSV file (in the future this
could also be a database) on which the algorithm can run. When the
algorithm is finished, it writes back the output to a different file.

The central part of the algorithm has to be able to create (sub)tasks.
These subtasks are responsible for executing the federated part of the
algorithm. The central part of the algorithm can either be executed on
one of the nodes in the vantage6 network or on the machine of a
researcher. In this example we only show the case in which one of the
nodes executes the central part of the algorithm. The node provides the
algorithm with a JWT token so that the central part of the algorithm has
access to the server to post these subtasks.

📂Algorithm Structure
~~~~~~~~~~~~~~~~~~~~~~

The algorithm needs to be structured as a Python
`package <https://packaging.python.org/tutorials/packaging-projects/>`__.
This way the algorithm can be installed within the Docker image. The
minimal file-structure would be:

.. code:: bash

   project_folder
   ├── Dockerfile
   ├── setup.py
   └── algorithm_pkg
       └── __init__.py

We also recommend adding a ``README.md``, ``LICENSE`` and
``requirements.txt`` to the *project_folder*.

setup.py
^^^^^^^^

Contains the setup method to create a package from your algorithm code.
Here you specify some details about your package and the dependencies it
requires.

.. code:: python

   from os import path
   from codecs import open
   from setuptools import setup, find_packages

   # we're using a README.md, if you do not have this in your folder, simply
   # replace this with a string.
   here = path.abspath(path.dirname(__file__))
   with open(path.join(here, 'README.md'), encoding='utf-8') as f:
       long_description = f.read()

   # Here you specify the meta-data of your package. The `name` argument is
   # needed in some other steps.
   setup(
       name='v6-average-py',
       version="1.0.0",
       description='vantage6 average',
       long_description=long_description,
       long_description_content_type='text/markdown',
       url='https://github.com/IKNL/v6-average-py',
       packages=find_packages(),
       python_requires='>=3.10',
       install_requires=[
           'vantage6-client',
           # list your dependencies here:
           # pandas, ...
       ]
   )

.. note::
    The ``setup.py`` above is sufficient in most cases. However if you want to
    do more advanced stuff (like adding static data, or a CLI) you can use the
    `extra arguments <https://packaging.python.org/guides/distributing-packages-using-setuptools/#setup-args>`__
    from ``setup``.

Dockerfile
^^^^^^^^^^

The Dockerfile contains the recipe for building the Docker image. Typically you
only have to change the argument ``PKG_NAME`` to the name of you package.
This name should be the same as as the name you specified in the
``setup.py``. In our case that would be ``v6-average-py``.

.. code:: bash

   # This specifies our base image. This base image contains some commonly used
   # dependancies and an install from all vantage6 packages. You can specify a
   # different image here (e.g. python:3). In that case it is important that
   # `vantage6-client` is a dependancy of you project as this contains the wrapper
   # we are using in this example.
   FROM harbor2.vantage6.ai/algorithms/algorithm-base

   # Change this to the package name of your project. This needs to be the same
   # as what you specified for the name in the `setup.py`.
   ARG PKG_NAME="v6-average-py"

   # This will install your algorithm into this image.
   COPY . /app
   RUN pip install /app

   # This will run your algorithm when the Docker container is started. The
   # wrapper takes care of the IO handling (communication between node and
   # algorithm). You dont need to change anything here.
   ENV PKG_NAME=${PKG_NAME}
   CMD python -c "from vantage6.tools.docker_wrapper import docker_wrapper; docker_wrapper('${PKG_NAME}')"

``__init__.py``
^^^^^^^^^^^^^^^

This contains the code for your algorithm. It is possible to split this
into multiple files, however the methods that should be available to the
researcher should be in this file. You can do that by simply importing
them into this file (e.g. ``from .average import my_nested_method``)

We can distinguish two types of methods that a user can trigger:

+-----------+-------------------------------------------+----------+--------------------+
| name      | description                               | prefix   | arguments          |
+===========+===========================================+==========+====================+
| master    | Central part of the algorithm. Receives a |          | ``(client, data,   |
|           | ``client`` as argument which provides an  |          | *args, **kwargs)`` |
|           | interface to the central server. This way |          |                    |
|           | the master can create tasks and collect   |          |                    |
|           | their results.                            |          |                    |
+-----------+-------------------------------------------+----------+--------------------+
| Remote    | Consumes the data at the node to compute  | `RPC_`   | ``(data, *args,    |
| procedure | the partial.                              |          | **kwargs)``        |
| call      |                                           |          |                    |
+-----------+-------------------------------------------+----------+--------------------+

.. warning::
    Everything that is returned by the\ ``return`` statement is sent back to the
    central vantage6-server. This should never contain any privacy-sensitive
    information.

.. warning::
    The ``client`` the master method receives is an ``AlgorithmClient`` (or a
    ``ContainerClient`` if you are using an older version), which is different
    than the client you use as a user.


For our average algorithm the implementation will look as follows:

.. code:: python

   import time

   from vantage6.tools.util import info

   def master(client, data, column_name):
       """Combine partials to global model

       First we collect the parties that participate in the collaboration.
       Then we send a task to all the parties to compute their partial (the
       row count and the column sum). Then we wait for the results to be
       ready. Finally when the results are ready, we combine them to a
       global average.

       Note that the master method also receives the (local) data of the
       node. In most usecases this data argument is not used.

       The client, provided in the first argument, gives an interface to
       the central server. This is needed to create tasks (for the partial
       results) and collect their results later on. Note that this client
       is a different client than the client you use as a user.
       """

       # Info messages can help you when an algorithm crashes. These info
       # messages are stored in a log file which is send to the server when
       # either a task finished or crashes.
       info('Collecting participating organizations')

       # Collect all organization that participate in this collaboration.
       # These organizations will receive the task to compute the partial.
       organizations = client.get_organizations_in_my_collaboration()
       ids = [organization.get("id") for organization in organizations]

       # Request all participating parties to compute their partial. This
       # will create a new task at the central server for them to pick up.
       # We've used a kwarg but is is also possible to use `args`. Although
       # we prefer kwargs as it is clearer.
       info('Requesting partial computation')
       task = client.create_new_task(
           input_={
               'method': 'average_partial',
               'kwargs': {
                   'column_name': column_name
               }
           },
           organization_ids=ids
       )

       # Now we need to wait untill all organizations(/nodes) finished
       # their partial. We do this by polling the server for results. It is
       # also possible to subscribe to a websocket channel to get status
       # updates.
       info("Waiting for results")
       results = client.wait_for_results(task_id=task.get("id"))

       # Now we can combine the partials to a global average.
       global_sum = 0
       global_count = 0
       for result in results:
           global_sum += result["sum"]
           global_count += result["count"]

       return {"average": global_sum / global_count}

   def RPC_average_partial(data, column_name):
       """Compute the average partial

       The data argument contains a pandas-dataframe containing the local
       data from the node.
       """

       # extract the column_name from the dataframe.
       info(f'Extracting column {column_name}')
       numbers = data[column_name]

       # compute the sum, and count number of rows
       info('Computing partials')
       local_sum = numbers.sum()
       local_count = len(numbers)

       # return the values as a dict
       return {
           "sum": local_sum,
           "count": local_count
       }

Local testing
~~~~~~~~~~~~~

Now that we have a vantage6 implementation of the algorithm it is time
to test it. Before we run it in a vantage6 setup we can test it locally
by using the ``ClientMockProtocol`` which simulates the communication
with the central server.

Before we can locally test it we need to (editable) install the
algorithm package so that the Mock client can use it. Simply go to the
root directory of your algorithm package (with the ``setup.py`` file)
and run the following:

.. code:: bash

   pip install -e .

Then create a script to test the algorithm:

.. code:: python

   from vantage6.tools.mock_client import ClientMockProtocol

   # Initialize the mock server. The datasets simulate the local datasets from
   # the node. In this case we have two parties having two different datasets:
   # a.csv and b.csv. The module name needs to be the name of your algorithm
   # package. This is the name you specified in `setup.py`, in our case that
   # would be v6-average-py.
   client = ClientMockProtocol(
       datasets=["local/a.csv", "local/b.csv"],
       module="v6-average-py"
   )

   # to inspect which organization are in your mock client, you can run the
   # following
   organizations = client.get_organizations_in_my_collaboration()
   org_ids = ids = [organization["id"] for organization in organizations]

   # we can either test a RPC method or the master method (which will trigger the
   # RPC methods also). Lets start by triggering an RPC method and see if that
   # works. Note that we do *not* specify the RPC_ prefix for the method! In this
   # example we assume that both a.csv and b.csv contain a numerical column `age`.
   average_partial_task = client.create_new_task(
       input_={
           'method':'average_partial',
           'kwargs': {
               'column_name': 'age'
           }
       },
       organization_ids=org_ids
   )

   # You can directly obtain the result (we dont have to wait for nodes to
   # complete the tasks)
   results = client.result.from_task(average_partial_task.get("id"))
   print(results)

   # To trigger the master method you also need to supply the `master`-flag
   # to the input. Also note that we only supply the task to a single organization
   # as we only want to execute the central part of the algorithm once. The master
   # task takes care of the distribution to the other parties.
   average_task = client.create_new_task(
       input_={
           'master': 1,
           'method':'master',
           'kwargs': {
               'column_name': 'age'
           }
       },
       organization_ids=[org_ids[0]]
   )
   results = client.result.from_task(average_task.get("id"))
   print(results)

Building and Distributing
~~~~~~~~~~~~~~~~~~~~~~~~~

Now that we have a fully tested algorithm for the vantage6
infrastructure. We need to package it so that it can be distributed to
the data-stations/nodes. Algorithms are delivered in Docker images. So
that's where we need the ``Dockerfile`` for. To build an image from our
algorithm (make sure you have docker installed and it's running) you can
run the following command from the root directory of your algorithm
project.

.. code:: bash

   docker build -t harbor2.vantage6.ai/demo/average .

The option ``-t`` specifies the (unique) identifier used by the
researcher to use this algorithm. Usually this includes the registry
address (harbor2.vantage6.ai) and the project name (demo).

.. note::
    In case you are using docker hub as registry, you do not have to specify
    the registry or project as these are set by default to the Docker hub and
    your docker hub username.

.. code:: bash

   docker push harbor2.vantage6.ai/demo/average

.. note::
    Reach out to us on `Discord <https://discord.gg/yAyFf6Y>`__ if you want to
    use our registries (harbor2.vantage6.ai and harbor2.vantage6.ai).
