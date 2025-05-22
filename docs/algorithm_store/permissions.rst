Permissions
-----------

Policies
~~~~~~~~

Algorithm store policies are defined by the algorithm store administrator and determine
the general permission and access rules for the algorithm store. Arguably, the most
important policy is who is allowed to view the algorithms in the store. For the
community store, this is set to public, meaning that anyone can view the algorithms. For
a private store, this can be set to private, meaning that only authorized users can
view the algorithms. Other examples of policies are e.g. setting how many reviewers
are required to approve an algorithm, or if reviewers should be from a different
organization as the algorithm developer.

Permission management
~~~~~~~~~~~~~~~~~~~~~

Apart from the policies, there are also access rules at the user level. Rules are used
to determine the actions that a user is allowed to take in the algorithm store.

In order to perform operations in the algorithm store, a user must be registered in the
algorithm store and must be authenticated. Then, rules can be assigned to the user to
give them the necessary permissions.

Permission rules
^^^^^^^^^^^^^^^^

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

Rules can be assigned to a user by another user who has at least the same permission level
as the rules assigned. Single rules can be assigned, but default combinations of rules
are available, as roles. The following default roles available in the algorithms store:

#. **Root**: Has all permissions.
#. **Developer**: Can submit new algorithms to the store and edit them before they are
   reviewed.
#. **Algorithm Manager**: Can assign reviewers to new algorithms, and manage
   algorithms. Whenever a new algorithm is submitted, users with permission to register
   new reviews are alerted, so users with this role as well as the root role will be
   alerted to assign reviewers (if an email server has been set up).
#. **Reviewer**: Can approve or reject algorithms that they have been requested to
   review.
#. **Viewer**: Can view all resources in the store.
#. **Store Manager**: Can manage the store's users and their permissions.

Note that all default roles have permission to view all resources. To give an example,
the permissions of a reviewer are shown below.

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