
.. _azure-blob-storage:

Azure Blob Storage
""""""""""""""""""

For algorithms that require large inputs or outputs, the default relational
database is not well suited. Azure blob storage can be used
instead. In this case, references to the inputs and results will be stored
in the database, whereas the actual data is stored in `Azure Blob Storage
<https://azure.microsoft.com/en-us/products/storage/blobs>`__. See
:ref:`server-configure` for more details on the configuration,
and :ref:`blob-storage` for more information.