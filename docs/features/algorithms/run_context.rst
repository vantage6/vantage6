.. _algo-run-context:

Run context
-----------

The ``run_context`` feature is an experimental step towards a more standard way
of providing an algorithm with everything it needs to carry out its specific
job.

The idea behind ``run_context`` is to expose an algorithm-readable JSON file
that conveys that information. It is meant for the algorithm itself to read.
It is **not** yet meant to be a stable cross-platform standard or a complete
description of the underlying executor.

Why this exists
^^^^^^^^^^^^^^^

The current way that context (which inputs, their paths, output path, arguments,
etc.) is conveyed by the node to the algorithm container is through a mix of
(base32-encoded) environment variables and written files. This creates a tight
coupling between the algorithm wrapper (``vantage6-algorithm-tools``) and the
platform. This means using other languages to write algorithms for vantage6 is
harder. It also means reusing algorithms written for vantage6 for other
platforms can be trickier.

Apart from other platforms and languages, some potential new features like
allowing the researcher to specify the role of a dataset for an algorithm or
to attach richer metadata to inputs and outputs were pushing the sensible
limits of what environment variables should perhaps reasonably be used for.


Current scope
^^^^^^^^^^^^^

When the experimental node configuration option ``run_context_file`` is enabled,
the node writes a ``run_context.json`` file for each algorithm run and exposes
its path inside the algorithm container via the ``RUN_CONTEXT_FILE`` environment
variable.

Algorithms can read it, or a more portable algorithm wrapper can be written to
make use of it. The current json file tries to describe, in a compact way:

- the selected algorithm entrypoint
- the positional and named arguments for that entrypoint
- the inputs made available to the algorithm
- the outputs the algorithm is expected to write
- a small amount of runtime metadata about where it's being executed
- other vantage6-specific metadata

This feature is intentionally minimal and still under development. The exact
field names and contents may change.

Early example
^^^^^^^^^^^^^

A very small demo algorithm using this approach is available here:
https://github.com/mdw-nl/average-py

It uses a lightweight Python helper library for reading and dispatching
``run_context.json`` here:
https://github.com/mdw-nl/run-context-py

This is conceptually similar to what ``vantage6-algorithm-tools`` does for the
current vantage6 runtime, but with the algorithm reading from
``RUN_CONTEXT_FILE`` instead of depending on the current vantage6-specific
environment-variable and file conventions.

Ideally, in the future, information necessary to communicate with other nodes
needed for the aggregator component of an algorithm could also be "standardized"
and included here.

Illustrative example
^^^^^^^^^^^^^^^^^^^^

The following example shows the current shape of the file. The comments are
explanatory only and are not part of the actual JSON file.

.. code:: javascript

    {
      // At the moment, this is a proposal/experiment, hence version 0.1.
      "schema_version": "0.1",
      // Method selected for this run. The running algorithm can use this to
      // pick a starting point within it
      "entrypoint": {
        "name": "my_function"
      },
      // Positional and named arguments from task input
      "arguments": {
        "positional": [],
        "named": {
          "column_name": "my_column"
        }
      },
      // Minimal runtime identity of the executing node. Provides some extra
      // context that the algorithm might need to use for its operation
      "executor": {
        "id": 17,
        "kind": "vantage6-node"
      },
      // Data sources the algorithm should use
      "inputs": [
        {
          "id": "default",
          "uri": "/mnt/data/default.csv",
          "type": "csv",
          // Eventually it might be better to move 'arguments'.* a level up
          "arguments": {
            "bind": "dataset"
          }
        },
        {
          // For example, a config file for the dataset itself
          "id": "default_config",
          "uri": "/mnt/data/default.yaml",
          "type": "other",
          // Eventually it might be better to move 'arguments'.* a level up
          "arguments": {
            "bind": "config"
          }
        }
      ],
      // For example, the researcher could have selected this input with:
      // {"label": "somelabel", "arguments": {"bind": "dataset"}}
      // Locations where results should be written
      "outputs": [
        {
          "id": "result",
          "uri": "/mnt/data/task_123/output"
        }
      ],
      // vantage6-specific run/task metadata
      // Perhaps, if this run context "standard" proves useful, some of these
      // keys can move upward out of this extra/out-of-standard
      // vantage6-specific section
      "x-vantage6": {
        "run_id": 10,
        "task_id": 123,
        "collaboration_id": 1,
        "token_file": "/mnt/data/task_123/token",
        "api_proxy": {
          "host": "http://proxyserver",
          "port": "8080",
          "api_path": ""
        },
        "temporary_directory": "/mnt/tmp"
      }
    }

How this relates to the current vantage6 runtime
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the researcher supplied ``arguments`` for a selected database when
creating the task, those values are included in the corresponding
``inputs[*].arguments`` object. Other top-level selector fields such as ``query``,
``sheet_name`` and ``preprocessing`` are not currently copied into run
context.

As mentioned, vantage6 algorithms already receive runtime context through the
existing vantage6-specific mechanism of written files and environment variables.
For example, some of the input/output paths and connection details that the node
shares with the algorithm container via environment variables as of version
v4.13.7 look something like this:

- ``INPUT_FILE``
- ``OUTPUT_FILE``
- ``HOST``
- ``USER_REQUESTED_DATABASE_LABELS``
- ``<DB_LABEL>_DATABASE_URI``

In the current node implementation, most node-provided environment variable
values are base32-encoded before they are injected into the algorithm
container. The Python algorithm tools decode them again when the wrapper starts.
Algorithms that use the standard vantage6 Python wrappers therefore continue to
use the existing interface unchanged.

The ``RUN_CONTEXT_FILE`` path is added to that existing list of environment
variables. Unlike most node-provided environment variable values, this path is
intentionally left plain so that algorithms can read it directly without
needing vantage6-specific awareness. Note that enabling
``run_context_file`` does not change the current way of passing information to
the algorithm container via files and environment variables. It is only an
addition; existing algorithms using ``vantage6-algorithm-tools`` should
continue to work as before. The only difference is that ``run_context.json``
will be created as well.

Current limitations
^^^^^^^^^^^^^^^^^^^

At the moment, the experimental ``run_context`` support does not yet model
several existing features, including:

- VPN and port-forwarding details
- SSH tunnel metadata
- whitelist / Squid proxy policy details
- linked Docker service aliases
- full environment-variable compatibility details
- etc.

In addition, the current ``run_context`` implementation only supports
file-based databases. If the feature is enabled and a task requests a non-file
database, the task start fails. This is done for security reasons, e.g. to
prevent database secrets from being present in additional files that may persist
for some time.

We have opened a discussion on this topic where more information can be found:
https://github.com/orgs/vantage6/discussions/2556
