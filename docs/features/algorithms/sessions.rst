Sessions
--------

Sessions have been added to vantage6 to provide a way to prepare a dataset that can be
re-used in many computation tasks. They are important to ensure that vantage6 can
interact with the data in a flexible and reproducible way.
Sessions are especially useful when the data is large and
querying it from the nodes is slow. Also, it allows for flexible pre-processing of the
data and storing the final result reliably and reusable.

A session is started by extracting data from one or more of the node's databases, and
can be submitted to as many pre-processing steps as required. When the data is ready,
the session can be used to perform as many computations on the data as you wish. It is
also possible to pre-process the data further after computation tasks have been executed.

Data that is extracted from a node database is added to the session as a dataframe. Each
session contains one or more data frames. These data frames can be used for computation
tasks. Some computation tasks may use all data frames in the session, while others may
just use one.

Sessions are related to the other entities in the following way:

.. uml::

    !theme superhero-outline

    rectangle Session
    rectangle DataFrame
    rectangle Column
    rectangle Node
    rectangle Collaboration
    rectangle Study
    rectangle User
    rectangle Task

    User "1" - "n" Session: \t
    Session "n" -- "1" Collaboration
    Collaboration "1" - "n" Study: \t
    Study "0" - "n" Session
    Session "1" - "n" DataFrame: \t
    DataFrame "1" - "n" Column: \t
    Column "1" - "n" Node: \t
    Task "n" -- "1" Session
    Task "0" - "1" DataFrame

Data frames are the representation of the data that will eventually be used in the most
important tasks - computation tasks that produces the research results. Data frames
provide the following features:

- The data is loaded in the data frames once and can then be used multiple times. This
  saves the time of having to load the data from the source every time a new task
  is executed. This is especially useful when the database is large and retrieving the
  data is slow.
- Data frames can be modified using pre-processing tasks. These can, for example, add or
  remove columns, or filter rows. The latest version of the data frame is used in the
  computation tasks. The data frame keeps track of the last task that modified it.
- Data frames can have different permission scopes. You can create data frames that are
  scoped to you, but you can also share them with other users in your organization or
  with the entire collaboration. Users with the organization or collaboration permission
  scope can also see, modify and delete data frames that are scoped to you within the
  organization or collaboration. In other words, scoping a data frame to yourself is
  not a way to keep the data frame private. If you scoped a data frame to your
  organization or collaboration, any user in the organization or collaboration can see
  the data frame.
- Data frames provide a standardized way to store data. This makes it easier to write
  algorithms that can be used across different collaborations.
- Data extraction, pre-processing and computation on the data are separated processes.
  This makes it easier to share algorithms with other projects. It even allows for the
  different steps to be written in different programming languages. Finally, it is also
  more secure, as the compute tasks no longer have access to the source data.
- Data frames have standardized metadata that they can share. This allows the
  infrastructure to provide the researchers with information about the data, such as
  which columns are available, and what the data types of those columns are.

Algorithm Step Types
^^^^^^^^^^^^^^^^^^^^

Every algorithm function that is being executed in a vantage6 network is one of the
following actions:

- ``data-extraction``: function to retrieve the data from the source, and store it in
  a data frame.
- ``pre-processing``: function to modify the data frame.
- ``compute``: function to use the data frame to answer a research question. This can be
  a machine learning model, a statistical analysis, or any other type of computation.

These actions are managed by the infrastructure. For example, the infrastructure ensures
that data extraction functions are the only functions that are allowed to access the
source data.

The ``compute`` action can be triggered by the user when the ``/task`` endpoint is used.
In the Python client this is done by calling the ``client.task.create()`` method. The
``data extraction`` and ``pre-processing`` actions are triggered when the ``/session``
endpoints are used. In the Python client this is done by calling the
``client.dataframe.create()`` methods and ``client.dataframe.preprocess()`` methods.



.. uml::
    :caption: An illustration of how the actions are related to each other. In this
        example, there are ``n`` pre-processing steps and ``m`` compute steps. First,
        the data is extracted. Then, the data is pre-processed. Finally, the data is
        used to compute the research results. Note that in this schema, the first
        compute task is done after the first pre-processing step - not after ``n``
        steps. At any point in the pre-processing steps, it is possible to send a task
        to the current data frame. It is thus also possible to execute a compute task
        directly after data extraction.
    !theme superhero-outline
    skinparam linetype ortho
    left to right direction


    package "Modify Session" {
        package "Data extraction" {
            rectangle Extract as A
        }
        package "Pre-processing" {
            rectangle "Step 1" as C
            rectangle "Step n" as D
        }
    }

    package "Compute" {
        rectangle 1 as E
        rectangle 2 as F
        rectangle m as M
    }

    rectangle Server as server

    A --> C
    C --> D
    C --> E
    D --> F
    D --> M
    E --> server
    F --> server
    M --> server

Dependent tasks
^^^^^^^^^^^^^^^

As described above, there are tasks that modify the data frame (``data extraction`` and
``pre-processing``) and tasks that compute on the data frame (``compute``). In order to
ensure that the data frame is not modified while another task is using it to compute
analysis results, the infrastructure ensures that such tasks are executed in the
proper order. This is done by making the tasks dependent on each other.

There are three senarions:

- A ``data-extraction`` task is not dependent on any other task.
- A ``pre-processing`` task is *always* dependent on the previous ``pre-processing`` or,
  in case there is none, the ``data-extraction`` task. But it is also dependent on all
  ``compute`` tasks that have been requested prior to the new ``pre-processing`` task.
- A ``compute`` task is *always* dependent on the last ``pre-processing`` task or, in
  case there is none, the ``data-extraction`` task.

.. uml::
    :caption: Example dependency tasks tree in a single dataframe. Note that (7) is
        not dependent on (4) as in this case (7) was requested after (4) was completed.

    !theme superhero-outline
    skinparam linetype polyline
    left to right direction

    rectangle "(1) Data Extraction" as data_extraction
    rectangle "(2) Compute 1" as compute_1
    rectangle "(3) Pre-processing 1" as pre_processing_1
    rectangle "(4) Compute 2" as compute_2
    rectangle "(5) Compute 3" as compute_3
    rectangle "(6) Pre-processing 2" as pre_processing_2
    rectangle "(7) Pre-processing 3" as pre_processing_3
    rectangle "(8) Compute 4" as compute_4

    data_extraction --> pre_processing_1
    data_extraction --> compute_1
    compute_1 --> pre_processing_2

    pre_processing_1 --> compute_2
    pre_processing_1 --> compute_3

    compute_3 --> pre_processing_3

    pre_processing_1 --> pre_processing_2
    pre_processing_2 --> pre_processing_3
    pre_processing_3 --> compute_4



Session storage
^^^^^^^^^^^^^^^
When a new session is created, each node creates a new session folder. In this folder,
the data frames and session log are stored. This log keeps track on which action was
performed on the data frame. You can inspect the log on the node by using the command
``parquet-tools show state.parquet``.

The session folder can also be used to share data between different tasks that are not
related to sessions, for example, when you need to store a secret key that is used in a
successor computation task. In the algorithms you can use the session folder with the
environment variable ``SESSION_FOLDER``.
