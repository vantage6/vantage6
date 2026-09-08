

.. _blob-storage:

Large Run-Data Store
--------------------

By default the vantage6 server stores task inputs and results directly
in the relational database. For deployments that handle large inputs
or results, the server can be configured to stream them to a separate
backend instead, identified by a top-level ``large_run_data_store``
key in the server config:

- ``"filesystem"`` — local filesystem (see :ref:`file-run-data-backend`).
- ``"azure"`` — Azure Blob Storage (see :ref:`azure-run-data-backend`).

If the key is omitted, the relational database is used. If the value
is not one of the two above the server refuses to start.

.. warning::
   The previous configuration shape used a single ``large_result_store``
   block with a ``type:`` field. That shape is no longer accepted —
   the server will raise a ``ValueError`` at startup if it is present.
   Migrate to the top-level ``large_run_data_store`` string described
   below.

.. _file-run-data-backend:

Filesystem backend
++++++++++++++++++

To stream run data to the local filesystem, set:

::

  large_run_data_store: "filesystem"

Run data is always written to ``/mnt/run_data`` inside the server
container. Where that path points to on the host depends on how the
server is launched.

Under docker-compose
~~~~~~~~~~~~~~~~~~~~

This is the recommended deployment path. Mount the host directory of
your choice to ``/mnt/run_data`` inside the server container:

::

  services:
    server:
      volumes:
        - ./my-run-data:/mnt/run_data

.. warning::
   For multi-replica deployments the host mount target must point at a
   shared filesystem (NFS, Azure Files, …). Replicas using local-only
   storage will not see each other's run data.

Under ``v6 server start``
~~~~~~~~~~~~~~~~~~~~~~~~~

The CLI automatically bind-mounts ``<server data dir>/run_data`` on
the host to ``/mnt/run_data`` in the container. There is no host-path
configuration to set; the CLI prints the resolved host path at
startup. This path is intended for local development; production
deployments should use the docker-compose path above.

Overriding the in-container path
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If for some reason the in-container path ``/mnt/run_data`` is
unavailable, set ``VANTAGE6_RUN_DATA_BASE_PATH`` on the server
container to override it (and mount whatever you want at that path
instead).

The env-var value is used **verbatim** as the storage root — nothing
is appended to it. Run-data entries land at
``{VANTAGE6_RUN_DATA_BASE_PATH}/{uuid[:2]}/{uuid}``. For example, with
``VANTAGE6_RUN_DATA_BASE_PATH=/var/lib/v6/runs`` and a run-data UUID
of ``abc12345-…``, the file is written to
``/var/lib/v6/runs/ab/abc12345-…``.

.. warning::
   This override is intended for the docker-compose path, where you
   control the bind-mount yourself. Under ``v6 server start`` the CLI
   always bind-mounts the host's ``<ctx.data_dir>/run_data`` to the
   container's ``/mnt/run_data`` and does **not** read the env var —
   setting ``VANTAGE6_RUN_DATA_BASE_PATH`` on a CLI-launched server
   would make the server read from a path the CLI did not mount, so
   run data would land inside the ephemeral container filesystem and
   be lost when the container exits.

On-disk layout
~~~~~~~~~~~~~~

Run-data entries are written under a two-character shard derived from
the UUID identifier (``{base_path}/{uuid[:2]}/{uuid}``) to keep
individual directories from growing without bound. Writes are atomic:
a tempfile is ``fsync``-ed and then renamed into place, so readers
never observe a half-written entry.

.. _azure-run-data-backend:

Azure backend
+++++++++++++

To stream run data to Azure Blob Storage, set
``large_run_data_store`` to ``"azure"`` and provide an
``azure_run_data_store`` block with the credentials:

::

  large_run_data_store: "azure"
  azure_run_data_store:
    container_name: test-container
    tenant_id: "your-tenant-id"
    client_id: "your-client-id"
    client_secret: "your-client-secret"
    storage_account_name: "your-storage-account-name"

The ``test-container`` value above refers to the Azure Blob Storage
container (unrelated to Docker containers) in which all run data is
stored. This container must be created in Azure beforehand.
Tenant id, client id and client secret are required for authentication
(for help on setting up a managed identity, see
`Authorize access to blobs using Azure Active Directory
<https://learn.microsoft.com/en-us/azure/storage/blobs/authorize-access-azure-active-directory>`__).

Development with Azurite
~~~~~~~~~~~~~~~~~~~~~~~~

For development and testing purposes, `Azurite
<https://github.com/Azure/Azurite>`__ can be used. There are subtle
differences between the two, so be aware that it will not be
completely representative of the production environment.

To use Azurite, a connection string can be configured instead of
service-principal credentials. The example below uses the Azurite
default connection string with endpoints adjusted to point at a local
Azurite instance:

::

  large_run_data_store: "azure"
  azure_run_data_store:
    container_name: test-container
    connection_string: "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://172.17.0.1:10000/devstoreaccount1;QueueEndpoint=http://172.17.0.1:10001/devstoreaccount1;"

.. warning::
   Connection strings are not recommended for production: the account
   name and key are stored in plaintext in the configuration, with no
   automatic rotation and no fine-grained RBAC permissions.

Developer documentation
+++++++++++++++++++++++

When configured to use the large run-data store, inputs and results
are streamed:

- From the user client, through the server, to the run-data store and vice versa
- From the node client, through the server, to the run-data store and vice versa
- From the algorithm container, through the proxy and server to the run-data store and vice versa

Whenever run data is uploaded, it is stored using a UUID as identifier.
This UUID is then used as the reference in the ``input`` or ``result``
field in the database. To ensure backwards compatibility, checks are
made throughout the code to determine whether a run was performed
using the relational database, in which case the ``input`` or
``result`` field should be interpreted as-is rather than as a pointer
into the run-data store.

The ``/blobstream`` endpoint on the server enables streaming of large
input and result data directly to and from the run-data store. This
reduces memory usage by never storing the entire input or result in
memory at once, and avoids storing large payloads in the database. (The
endpoint name predates the rename; it is kept for wire-API
compatibility.)

Encryption
~~~~~~~~~~

Since inputs and results are now uploaded and downloaded separately and are no longer part of
a larger JSON object, Base64 encoding is skipped when data is encrypted. The encrypted raw bytes
can be stored directly.
Inputs are encrypted before uploading, and results are decrypted after downloading in the node and client.
Since encryption and decryption for the algorithm container takes place in the proxy, for the algorithm
encryption and decryption is done on a chunk by chunk basis using **AES-CTR** to prevent loading the entire
input or result into memory at once.

Database
~~~~~~~~

A ``blob_storage_used`` column is present on the ``runs`` table to
indicate whether the large run-data store and streaming was used for
that run. This ensures for any run it is clear whether the ``input``
or ``result`` field should be interpreted directly, or first
retrieved. For existing installations, empty values for
``blob_storage_used`` are assumed to be ``False``. (The column name
predates the rename; it is kept for database-schema compatibility.)
