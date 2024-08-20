.. _algorithm-store:

Introduction
------------

What is an algorithm store?
"""""""""""""""""""""""""""

When using vantage6, it is important to know which algorithms are available
to you. This is why vantage6 has algorithm stores. An algorithm store contains
metadata about the algorithms so that you can easily find the algorithm you
need, and know how to use it.

.. _community-store:

Community store
"""""""""""""""

There is a community algorithm store hosted at https://store.cotopaxi.vantage6.ai.
This store is maintained by the vantage6 community and allows you to easily reuse
algorithms developed by others. You can also create your own algorithm store.
This allows you to create a private algorithm store, which is only available to your
own collaborations.

.. # TODO add link to creating algorithm store
.. TODO add links to an architectural page where algorithm store is explained

.. _algorithm-store-linking:

Linking algorithm stores
""""""""""""""""""""""""

Algorithm stores can be linked to a vantage6 server or to a specific
collaboration on a server. If an algorithm store is linked to a server, the
algorithms in the store are available to all collaborations on that server. If
an algorithm store is linked to a collaboration, the algorithms in the store
are only available to that collaboration.

Users can link algorithm stores to a collaboration if they have permission to
modify that collaboration. Algorithm stores can only be linked to a server by
users that have permission to modify all collaborations on the server.

To link an algorithm store, go to the collaboration settings page on the UI or use
the Python client function `client.store.create()`. When linking a store to a server,
you need to provide the algorithm store URL, a name to refer to the store, and the
collaboration ID of the collaboration you want to link the store to. Alternatively,
you can link a store to all collaborations on the server by not providing a
collaboration ID.