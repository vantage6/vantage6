.. _algorithm-store-api-refs:

Algorithm store
===============

.. automodule:: vantage6.algorithm.store

Main class of algorithm store
-----------------------------

vantage6.algorithm.store
++++++++++++++++++++++++

.. autoclass:: vantage6.algorithm.store.AlgorithmStoreApp
    :members:

.. autofunction:: vantage6.algorithm.store.run_server

.. autofunction:: vantage6.algorithm.store.run_dev_server

API endpoints
-------------

.. warning::
    The API endpoints are documented on the ``/apidocs`` endpoint of the
    server (e.g. ``https://cotopaxi.vantage6.ai/apidocs``). That documentation
    requires a different format than the one used to create this documentation.
    We are therefore not including the API documentation here. Instead, we
    merely list the supporting functions and classes.

vantage6.algorithm.store.resource
++++++++++++++++++++++++

.. automodule:: vantage6.algorithm.store.resource
    :members:

vantage6.algorithm.store.resource.schema.output_schema
+++++++++++++++++++++++++++++++++++++++++++++

.. automodule:: vantage6.algorithm.store.resource.schema.output_schema
    :members:

vantage6.algorithm.store.resource.schema.input_schema
+++++++++++++++++++++++++++++++++++++++++++++

.. automodule:: vantage6.algorithm.store.resource.schema.input_schema
    :members:

SQLAlchemy models
-----------------

vantage6.algorithm.store.model.base
++++++++++++++++++++++++++

This module contains a few base classes that are used by the other models.

.. automodule:: vantage6.algorithm.store.model.base
    :members:

Database models for the API resources
+++++++++++++++++++++++++++++++++++++

vantage6.algorithm.store.model.algorithm
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.algorithm.store.model.algorithm.Algorithm
    :members:
    :exclude-members: id

vantage6.algorithm.store.model.argument
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.algorithm.store.model.argument.Argument
    :members:
    :exclude-members: id

vantage6.algorithm.store.model.database
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.algorithm.store.model.database.Database
    :members:
    :exclude-members: id

vantage6.algorithm.store.model.function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.algorithm.store.model.function.Function
    :members:
    :exclude-members: id

vantage6.algorithm.store.model.vantage6_server
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.algorithm.store.model.vantage6_server.Vantage6Server
    :members:
    :exclude-members: id