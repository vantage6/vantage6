.. _server-api-refs:

Server
======

.. automodule:: vantage6.server


Main server class
-------------------

vantage6.server.ServerApp
+++++++++++++++++++++++++

.. autoclass:: vantage6.server.ServerApp
    :members:

Starting the server
-------------------

vantage6.server.run_server
++++++++++++++++++++++++++

.. autofunction:: vantage6.server.run_server

.. warning::
    Note that the ``run_server`` function is normally not used directly to
    start the server, but is used as utility function in places that start the
    server. The recommended way to start a server is using uWSGI as is done in
    ``vserver start``.

.. todo and in wsgi.py!
.. todo add refs for statement above

vantage6.server.run_dev_server
++++++++++++++++++++++++++++++

.. autofunction:: vantage6.server.run_dev_server

Permission management
---------------------

vantage6.server.model.rule.Scope
+++++++++++++++++++++++++++++++++

.. autoclass:: vantage6.server.model.rule.Scope
    :members:
    :undoc-members:

vantage6.server.model.rule.Operation
++++++++++++++++++++++++++++++++++++

.. autoclass:: vantage6.server.model.rule.Operation
    :members:
    :undoc-members:

vantage6.server.model.permission.RuleCollection
+++++++++++++++++++++++++++++++++++++++++++++++

.. autoclass:: vantage6.server.permission.RuleCollection
    :members:

vantage6.server.permission.PermissionManager
+++++++++++++++++++++++++++++++++++++++++++++

.. autoclass:: vantage6.server.permission.PermissionManager
    :members:

Socket functionality
--------------------

vantage6.server.websockets.DefaultSocketNamespace
++++++++++++++++++++++++++++++++++++++++++++++++++

.. autoclass:: vantage6.server.websockets.DefaultSocketNamespace
    :members:

API endpoints
-------------

.. warning::
    The API endpoints are also documented on the ``/apidocs`` endpoint of the
    server (e.g. ``https://cotopaxi.vantage6.ai/apidocs``). That documentation
    requires a different format than the one used here. We are therefore
    not including the API documentation here. Instead, we merely list the
    supporting functions and classes.

vantage6.server.resource
++++++++++++++++++++++++

.. automodule:: vantage6.server.resource
    :members:

vantage6.server.resource.common.output_schema
+++++++++++++++++++++++++++++++++++++++++++++

.. todo This output isn't pretty at the moment, check in v4.0 if this is
    still the case (there that module is rewritten)

.. automodule:: vantage6.server.resource.common.output_schema
    :members: HATEOASModelSchema, create_one_to_many_link

vantage6.server.resource.common.auth_helper
+++++++++++++++++++++++++++++++++++++++++++

.. automodule:: vantage6.server.resource.common.auth_helper
    :members:

vantage6.server.resource.common.swagger_template
+++++++++++++++++++++++++++++++++++++++++++++++++

This module contains the template for the OAS3 documentation of the API.

SQLAlchemy models
-----------------

vantage6.server.model.base
++++++++++++++++++++++++++

This module contains a few base classes that are used by the other models.

.. automodule:: vantage6.server.model.base
    :members:


Database models for the API resources
+++++++++++++++++++++++++++++++++++++

vantage6.server.model.algorithm_port.AlgorithmPort
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.server.model.algorithm_port.AlgorithmPort
    :members:
    :exclude-members: id

vantage6.server.model.authenticatable.Authenticatable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.server.model.authenticatable.Authenticatable
    :members:
    :exclude-members: id

vantage6.server.model.collaboration.Collaboration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.server.model.collaboration.Collaboration
    :members:
    :exclude-members: id

vantage6.server.model.node.Node
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.server.model.node.Node
    :show-inheritance:
    :members:
    :exclude-members: id

vantage6.server.model.organization.Organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.server.model.organization.Organization
    :members:
    :exclude-members: id

vantage6.server.model.run.Run
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.server.model.run.Run
    :members:
    :exclude-members: id

vantage6.server.model.role.Role
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.server.model.role.Role
    :members:
    :exclude-members: id

vantage6.server.model.rule.Rule
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.server.model.rule.Rule
    :members:
    :exclude-members: id

vantage6.server.model.task.Task
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.server.model.task.Task
    :members:
    :exclude-members: id

vantage6.server.model.user.User
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: vantage6.server.model.user.User
    :members:
    :show-inheritance:
    :exclude-members: id

Database models that link resources together
++++++++++++++++++++++++++++++++++++++++++++

.. todo these tables don't look right yet when they are rendered

vantage6.server.model.Member
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vantage6.server.model.member

.. autoclass:: vantage6.server.model.member.Member
    :members:
    :exclude-members: id

vantage6.server.model.permission
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vantage6.server.model.permission

.. autoclass:: vantage6.server.model.permission.Permission
    :members:

.. autoclass:: vantage6.server.model.permission.UserPermission
    :members:

vantage6.server.model.role_rule_association
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. automodule:: vantage6.server.model.role_rule_association

.. autoclass:: vantage6.server.model.role_rule_association.role_rule_association
    :members:


Database utility functions
--------------------------

vantage6.server.db
++++++++++++++++++

.. automodule:: vantage6.server.db
    :members:

Mail service
------------

vantage6.server.mail_service
++++++++++++++++++++++++++++

.. autoclass:: vantage6.server.mail_service.MailService
    :members:

Default roles
-------------

vantage6.server.default_roles
+++++++++++++++++++++++++++++

.. autofunction:: vantage6.server.default_roles.get_default_roles

Custom server exceptions
------------------------

vantage6.server.exceptions
++++++++++++++++++++++++++

.. automodule:: vantage6.server.exceptions
    :members:


.. todo add files in vantage6.server.controller?
.. todo add files in vantage6.server.configuration?
