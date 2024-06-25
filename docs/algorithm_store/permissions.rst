Permission management
---------------------

The permission system of the Algorithm Store is based on a combination of policies and rules.
Policies are used to define general access rules from external entities (i.e. users, vantage6 servers),
while rules are used to determine the actions that a user is allowed to take in the algorithm store.

In order to perform operations in the algorithm store, a user must be registered in the
algorithm store and must be authenticated.
A user account is linked to a whitelisted vantage6 server, and the authentication is performed
by logging in though the vantage6 server and using the obtained token to run a request on
a resource's endpoint.

Permission rules
~~~~~~~~~~~~~~~~

Just like in the vantage6 server, in the algorithm store rules are use to allow
or prevent a user from performing an operation.
An operation is an action that can be performed on a resource of the algorithm store.
There are 5 operations defined:

#. Create
#. Delete
#. Edit
#. Review
#. View

These operations can be performed on the available resources according to the following schema:

.. figure:: /images/rules-algo-store-overview.png
   :alt: Rule overview
   :align: center
|
Rules can be assigned to a user by another user who has at least the same permission level
as the rules assigned. Single rules can be assigned, but default combinations of rules are available,
as roles. There are 5 roles available in the algorithms store:

#. Developer
#. Reviewer
#. Root
#. Store Manager
#. Viewer

Root user has all the permissions.
The default set of rules assigned to the other roles are showed here below:

.. figure:: /images/rules-algo-store-developer.png
   :alt: Rule overview
   :align: center
|
.. figure:: /images/rules-algo-store-reviewer.png
   :alt: Rule overview
   :align: center
|
.. figure:: /images/rules-algo-store-manager.png
   :alt: Rule overview
   :align: center
|
.. figure:: /images/rules-algo-store-viewer.png
   :alt: Rule overview
   :align: center
