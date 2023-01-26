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

Socket functionality
--------------------

.. autoclass:: vantage6.server.websockets.DefaultSocketNamespace
    :members:

API endpoints
-------------

.. warning::
    The API endpoints are also documented on the ``/apidocs`` endpoint of the
    server (e.g. ``https://petronas.vantage6.ai/apidocs``). We are therefore
    not including the API documentation here. Instead, we merely list the
    supporting functions and classes.

.. todo Include HATEOAS models, but these should be rewritten soon.
.. todo consider including the auth_helper functions

SQLAlchemy models
-----------------

Helper (base) classes
~~~~~~~~~~~~~~~~~~~~~

.. .. autoclass:: vantage6.server.model.base.ModelBase
..     :members:

.. .. autoclass:: vantage6.server.model.base.Database
..     :members:

.. .. autoclass:: vantage6.server.model.base.DatabaseSessionManager
..     :members:

.. automodule:: vantage6.server.model.base
    :members:


Database models for the API resources
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.server.model.algorithm_port.AlgorithmPort
    :members:
    :exclude-members: id

.. autoclass:: vantage6.server.model.authenticatable.Authenticatable
    :members:
    :exclude-members: id

.. autoclass:: vantage6.server.model.collaboration.Collaboration
    :members:
    :exclude-members: id

.. autoclass:: vantage6.server.model.node.Node
    :show-inheritance:
    :members:
    :exclude-members: id

.. autoclass:: vantage6.server.model.organization.Organization
    :members:
    :exclude-members: id

.. autoclass:: vantage6.server.model.result.Result
    :members:
    :exclude-members: id

.. autoclass:: vantage6.server.model.role.Role
    :members:
    :exclude-members: id

.. autoclass:: vantage6.server.model.rule.Rule
    :members:
    :exclude-members: id

.. autoclass:: vantage6.server.model.task.Task
    :members:
    :exclude-members: id


.. autoclass:: vantage6.server.model.user.User
    :members:
    :show-inheritance:
    :exclude-members: id

Database models that link resources together
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. todo these tables don't look right yet when they are rendered

.. automodule:: vantage6.server.model.member

.. autoclass:: vantage6.server.model.member.Member
    :members:
    :exclude-members: id

------------------

.. automodule:: vantage6.server.model.permission

.. autoclass:: vantage6.server.model.permission.Permission
    :members:

.. autoclass:: vantage6.server.model.permission.UserPermission
    :members:

-------------------

.. automodule:: vantage6.server.model.role_rule_association

.. autoclass:: vantage6.server.model.role_rule_association.role_rule_association
    :members:

Mail service
------------

.. autoclass:: vantage6.server.mail_service.MailService
    :members:

Default roles
-------------

.. autofunction:: vantage6.server.default_roles.get_default_roles

