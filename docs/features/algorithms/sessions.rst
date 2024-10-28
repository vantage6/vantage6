Sessions
--------

Sessions are an important feature as all functions executed on the data are connected
to a session.

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

Sessions provide a way to store data between different tasks. A session can contain
several data frames. A data frame is constructed from the source data. These data
frames can be used for computation tasks.

Data frames provide the following features:

- They allow for the data to be loaded once and then used multiple times. This
  saves the time of having to load the data from the source every time a new task
  is executed. This is especially useful when the data is large and the source
  is slow.
- They allow to be modified. For example by adding or removing columns, or by
  filtering rows. This can be useful when the data needs to be preprocessed before
  it can be used in a computation task.
- They can be shared with other users in their organization or with the entire
  collaboration.
- They provide a standardized way to store data. This makes it easier to write
  algorithms that can be used in multiple collaborations.
- Data extraction, pre-processing and computation on the data are seperated processes.

  - This makes it easier to share algorithms with other projects.
  - The different steps can be written in different programming languages.
  - There is more security, as the compute tasks no longer have access to the source data.

- Data frames can share standardized metadata. This makes it easier to provide
  information about the data to the users of the data.

Function actions
^^^^^^^^^^^^^^^^
Every function that is being executed in a vantage6 network is linked to one of the
following actions:

- ``data-extraction``: function to retrieve the data from the source, and store it in
  a data frame.
- ``pre-processing``: function to modify the data frame.
- ``compute``: function to perform the computation on the data frame.

.. uml::

    !theme superhero-outline
    skinparam linetype ortho
    left to right direction


    package "Modify Session" {
        package "data-extraction" {
            rectangle step as A
        }
        package "pre-processing" {
            rectangle "step 1" as C
            rectangle "step n" as D
        }
    }

    package "compute" {
        rectangle 1 as E
        rectangle 2 as F
        rectangle N as N
    }

    rectangle server as server

    A --> C
    C --> D
    C --> E
    D --> F
    D --> N
    E --> server
    F --> server
    N --> server


These actions are managed by the infrastructure. For example, the infrastructure ensures
that the data-extraction function is the only function that has access to the source
data.

The ``compute`` action can be triggered by the user when the ``/task`` endpoint is used.
In the Python client this is done by calling the ``client.task.create()`` method. The
``data-extraction`` and ``pre-processing`` actions are triggered when the ``/session``
endpoints are used. In the Python client this is done by calling the
``client.dataframe.create()`` methods and ``client.dataframe.preprocess()`` methods.

Dependent tasks
^^^^^^^^^^^^^^^
There are basically two different types of tasks:

- Tasks that modify the data frame. These tasks are executing a ``data-extraction``
  or a ``pre-processing`` action.
- Tasks that are computing on the data frame. These tasks are executing a ```compute```
  action.

In order to ensure that the data frame is not modified while a task is computing on it,
the infrastructure ensures that the tasks are executed in the correct order. This is
done by making the tasks dependent on each other.

There are three senarions:

- A ``data-extraction`` task is not dependent on any other task.
- A ``pre-processing`` task is *always* dependent on the previous ``pre-processing`` or,
  in case there is none, the ``data-extraction`` task. But it is also dependent on all
  ``compute`` tasks that have been requested prior to the new ``pre-processing`` task.
- A ``compute`` task is *always* dependent on the last ``pre-processing`` task or in case
  there is none the ``data-extraction`` task.

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
When a new session is created each node creates a new session folder. In this folder,
the data frames and session log are stored. This log keeps track on which action was
performed on the data frame. You can inspect the log on the node by using the command
``parquet-tools show state.parquet``.

The session folder can also be used to share data between different tasks that are not
related to sessions, for example, when you need to store a secret key that is used in a
successor computation task. In the algorithms you can use the session folder by using
the environment variable ``SESSION_FOLDER``.
