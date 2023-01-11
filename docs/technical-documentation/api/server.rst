.. _server-api-refs:

Server
======

.. automodule:: vantage6.server


Main server class
-------------------

.. autoclass:: vantage6.server.ServerApp
    :members:

Starting the server
-------------------

.. autofunction:: vantage6.server.run_server

.. warning::
    Note that the ``run_server`` function is normally not used directly to
    start the server, but is used as utility function in places that start the
    server. The recommended way to start a server is using uWSGI as is done in
    ``vserver start``.

.. todo and in wsgi.py!
.. todo add refs for statement above

.. autofunction:: vantage6.server.run_dev_server

Permission management
---------------------

.. autoclass:: vantage6.server.model.rule.Scope
    :members:
    :undoc-members:

.. autoclass:: vantage6.server.model.rule.Operation
    :members:
    :undoc-members:

.. autoclass:: vantage6.server.permission.RuleCollection
    :members:

.. autoclass:: vantage6.server.permission.PermissionManager
    :members:

Mail service
------------

.. autoclass:: vantage6.server.mail_service.MailService
    :members:

Default roles
-------------

.. autofunction:: vantage6.server.default_roles.get_default_roles

