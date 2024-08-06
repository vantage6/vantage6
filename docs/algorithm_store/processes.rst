Store processes
---------------

The algorithm store manages the lifecycle of vantage6 algorithms, from its initial
submission by the algorithm developer to the running of the algorithm and finally its
replacement by a newer version. This page intends to give an overview of these processes.

Algorithm submission
^^^^^^^^^^^^^^^^^^^^

The first step in the lifecycle of an algorithm is its submission to the algorithm store.
An algorithm developer can do this via the algorithm store section of the UI or by using
the Python client's command `client.algorithm.create()`. The algorithm developer needs
to provide data such as a name, description, where to find the code and the docker
image, and which functions the algorithm provides and how to call them.

Each function of the algorithm is described, apart from its name and description, by the
following fields:

- **Parameters**: A list of parameters that the function expects. Each parameter has a
  name, a description, and a type. For example, if you want to compute an average, a
  parameter could be a column name. Apart from standard data types like integers,
  strings and booleans, vantage6 also supports *organizations* and *columns* as parameter
  types. When using these types, the user interface knows to show a dropdown with the
  available organizations or columns.

- **Databases**: A list of databases that the function expects. Most algorithms use a
  single database, but some algorithms might need multiple databases (e.g. one with
  patient data and another with population data). Each database has a name
  and a description. The user interface will show a dropdown with the available databases
  when the user needs to select a database.

- **Visualizations**: A list of visualizations that the function can produce. Each
  visualization has a name, a description, and a type. When viewing the results of an
  algorithm run in the UI, the UI will attempt to plot the results if a visualization
  is available. Depending on the visualization type, additional data might be required.
  For instance, for a line graph, the algorithm developer can set the x-axis and y-axis
  columns that should be visualized.

Algorithm review
^^^^^^^^^^^^^^^^

After an algorithm is submitted, it needs to undergo a review process. First, one or
more reviewers have to be assigned. Depending on their permissions, the algorithm
developer can do this themselves or a store manager can assign reviewers. The reviewers
can then view the algorithm and provide feedback. If the algorithm is approved, it will
be shown as approved in the UI and can be used to run tasks. While the algorithm is
under review, it is not yet available for running tasks in the UI.

Regularly, a developer has submitted an update to an algorithm that was already
approved. In such cases, when the changes are approved, the algorithm store will
invalidate the previous version of the algorithm. This means that the previous version
can then no longer be used to run tasks. It is also possible to invalidate an algorithm
without superseding it with a new version. This can be useful if an algorithm is found
to be faulty or if it is no longer needed.
