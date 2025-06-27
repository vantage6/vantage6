.. _algorithm-store-policies:

Recommended algorithm store policies
------------------------------------

Setting up an :ref:`algorithm store <algorithm-store>` is useful to collect all algorithms that are
relevant to your project. By having an algorithm store, you can choose to only make
algorithms from this store available to the researchers in your project.

The algorithm store allows for the definition of several policies around
algorithm review. The following policies are recommended when using the algorithm on
sensitive data:

- Each algorithm must be reviewed by at least two reviewers.
- The reviewers must not be involved in the development of the algorithm.
- At least one reviewer is a member of a different organization than the
  developer.
- If the developer also has the store manager role, they should not be allowed to
  assign reviews for their own algorithms.
- If a store manager also has the reviewer role, they may be allowed to assign
  themselves as a reviewer.

To ascertain that these policies are followed, they can be enforced by the
algorithm store wherever possible. For instance, if an algorithm
must be reviewed by at least two reviewers, an algorithm will simply not become
available when just a single reviewer approves the algorithm. However, not all
policies can be fully enforced from the software: if developers A and B
collaborate on an algorithm, and A submits it, the algorithm store does not know
that B was involved in developing the algorithm, so it will not be able to
prevent assignment of B as a reviewer.

Together, the recommended policies ensure that at least three authenticated
researchers (a developer and two reviewers) of at least two different institutes
in your project must be involved to approve an algorithm. By involving three trusted
researchers in the process, the risk of approving an inadequate algorithm is minimized.

.. note::

    The policies above could be implemented in the algorithm store configuration file
    as follows:

    .. code-block:: yaml

        policies:
            min_reviewers: 2
            assign_review_own_algorithm: false
            min_reviewing_organizations: 2
            # ... <other policies>

