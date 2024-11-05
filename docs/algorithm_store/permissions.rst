Permissions
-----------

Policies
~~~~~~~~

Algorithm store policies are defined by the algorithm store administrator and determine
the general permission and access rules for the algorithm store. Arguably the most
important policy is who is allowed to view the algorithms in the store. For the
community store, this is set to public, meaning that anyone can view the algorithms. For
a private store, this can be set to private, meaning that only authorized users can
view the algorithms. Other policies can be set to define which vantage6 servers are
allowed to access the store, or to shape the review process (e.g. how many reviewers
are required, or if they should be from a different organization as the algorithm
developer).

Permission management
~~~~~~~~~~~~~~~~~~~~~

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
   * - Whitelisted server
     - N/A
     - N/A
     - N/A
     - ✅

Note that not some permissions are not defined, because they do not correspond to any
existing operation that requires permission.

Rules can be assigned to a user by another user who has at least the same permission level
as the rules assigned. Single rules can be assigned, but default combinations of rules
are available, as roles. The following default roles available in the algorithms store:

#. **Root**: Has all permissions.
#. **Developer**: Can submit new algorithms to the store and edit them before they are
   reviewed.
#. **Algorithm Manager**: Can assign reviewers to new algorithms, and submit and delete
   algorithms. Whenever a new algorithm is submitted, users with these role are alerted
   by email to assign reviewers (if an email server has been set up). If no users have
   this role, all users with permission to assign reviewers will be alerted.
#. **Reviewer**: Can approve or reject algorithms that they have been requested to
   review.
#. **Viewer**: Can view all resources in the store.
#. **Store Manager**: Can manage the store's users and their permissions.
#. **Server Manager**: This role is automatically given to the user that whitelists
   their vantage6 server in the algorithm store. This role only gives them permission to
   undo the whitelisting of their server.

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
   * - Whitelisted server
     -
     -
     -
     - ❌