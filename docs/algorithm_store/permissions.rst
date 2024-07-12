Permission management
---------------------

The permission system of the algorithm store is based on a combination of policies and rules.
Policies are used to define general access rules from external entities (i.e. users, vantage6 servers),
while rules are used to determine the actions that a user is allowed to take in the algorithm store.
An example of a policy is a setting that anyone has read-only access to the algorithm store
even if they are not authenticated. An example of a rule is that a certain user is given permission
to submit new algorithms to the store.

In order to perform operations in the algorithm store, a user must be registered in the
algorithm store and must be authenticated.
A user account is linked to a whitelisted vantage6 server, and the authentication is performed
by logging in though the vantage6 server and using the obtained token to run a request on
an algorithm store resource endpoint.

Permission rules
~~~~~~~~~~~~~~~~

Just like in the vantage6 server, in the algorithm store rules are used to allow
or prevent a user from performing an operation.
An operation is an action that can be performed on a resource of the algorithm store.
The following operations are defined:

#. Create
#. Delete
#. Edit
#. View

These operations can be performed on the available resources according to the following schema:

.. list-table::
   :name: rules-algo-store
   :widths: 20 20 20 20 20

   * - Resource
     - View
     - Create
     - Edit
     - Delete
   * - Algorithm
     - ✅
     - ✅
     - ✅
     - ✅
   * - User
     - ✅
     - ✅
     - ✅
     - ✅
   * - Role
     - ✅
     - ✅
     - ✅
     - ✅
   * - Review
     - ✅
     - ✅
     - ✅
     - ✅
   * - Whitelisted server
     - N/A
     - N/A
     - N/A
     - ✅

Note that not some permissions are not defined, e.g.

Rules can be assigned to a user by another user who has at least the same permission level
as the rules assigned. Single rules can be assigned, but default combinations of rules are available,
as roles. There are 5 roles available in the algorithms store:

#. Developer
#. Reviewer
#. Root
#. Store Manager
#. Viewer

Root user has all the permissions. Other roles have a subset of the permissions - you
can view the permissions of other roles via UI or one of the other clients. To give an
example, the permissions of a reviewer are shown below. Note that they can view all
resources, and otherwise are only allowed to review algorithms. Other roles, such as
the developer, have permissions to create and edit algorithms but cannot review them.

.. list-table::
   :name: rules-algo-store-reviewer
   :widths: 20 20 20 20 20

   * - Resource
     - View
     - Create
     - Edit
     - Delete
   * - Algorithm
     - ✅
     - ❌
     - ❌
     - ❌
   * - User
     - ✅
     - ❌
     - ❌
     - ❌
   * - Role
     - ✅
     - ❌
     - ❌
     - ❌
   * - Review
     - ✅
     - ❌
     - ✅
     - ❌
   * - Whitelisted server
     -
     -
     -
     - ❌