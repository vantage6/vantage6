.. _configure-node:

Configure
---------

The vantage6-node requires a configuration file to run. This is a
``yaml`` file with a specific format.

The next sections describes how to configure the node. It first provides a few
quick answers on setting up your node, then shows an example of all
configuration file options, and finally explains where your vantage6
configuration files are stored.

How to create a configuration file
""""""""""""""""""""""""""""""""""

The easiest way to create an initial
configuration file is via: ``v6 node new``. This allows you to configure the
basic settings. For more advanced configuration options, which are listed below,
you can view the :ref:`example configuration file <node-configure-structure>`.

Where is my configuration file?
"""""""""""""""""""""""""""""""

To see where your configuration file is located, you can use the following
command

.. code:: bash

    v6 node files

.. warning::
    This command will not work if you have put your configuration file in a
    custom location. Also, you may need to specify the ``--system`` flag
    if you put your configuration file in the
    :ref:`system folder <node-configure-location>`.

.. _node-configure-structure:

All configuration options
"""""""""""""""""""""""""

The following configuration file is an example that intends to list all possible
configuration options.

You can download this file here: :download:`node_config.yaml`

.. literalinclude :: node_config.yaml

.. _node-configure-location:

Configuration file location
"""""""""""""""""""""""""""

The directory where the configuration file is stored depends on your
operating system (OS). It is possible to store the configuration file at
**system** or at **user** level. By default, node configuration files
are stored at **user** level, which makes this
configuration available only for your user.

The default directories per OS are as follows:

+-------------+-------------------------+--------------------------------+
| **Operating | **System-folder**       | **User-folder**                |
| System**    |                         |                                |
+=============+=========================+================================+
| Windows     | |win_sys|               | |win_usr|                      |
+-------------+-------------------------+--------------------------------+
| MacOS       | |mac_sys|               | |mac_usr|                      |
+-------------+-------------------------+--------------------------------+
| Linux       | |lin_sys|               | |lin_usr|                      |
+-------------+-------------------------+--------------------------------+

.. |win_sys| replace:: ``C:\ProgramData\vantage\node\``
.. |win_usr| replace:: ``C:\Users\<user>\AppData\Local\vantage\node\``
.. |mac_sys| replace:: ``/Library/Application/Support/vantage6/node/``
.. |mac_usr| replace:: ``/Users/<user>/Library/Application Support/vantage6/node/``
.. |lin_sys| replace:: ``/etc/vantage6/node/``
.. |lin_usr| replace:: ``/home/<user>/.config/vantage6/node/``

.. note::
    The command ``v6 node`` looks in these directories by default. However, it is
    possible to use any directory and specify the location with the ``--config``
    flag. But note that doing that requires you to specify the ``--config``
    flag every time you execute a ``v6 node`` command!

    Similarly, you can put your node configuration file in the system folder
    by using the ``--system`` flag. Note that in that case, you have to specify
    the ``--system`` flag for all ``v6 node`` commands.

.. _node-configure-security:

Security
""""""""

As a data owner it is important that you take the necessary steps to
protect your data. Vantage6 allows algorithms to run on your data and
share the results with other parties. It is important that you review
the algorithms before allowing them to run on your data.

Once you approved the algorithm, it is important that you can verify
that the approved algorithm is the algorithm that runs on your data.
There are two important steps to be taken to accomplish this:

-  Setting policies on the allowed algorithms in the ``policies`` section
   of the node-configuration file. You can specify a list of regex expressions
   here. Some examples of what you could define (note that these examples overlap so
   in practice you would not use all of them):

   .. code:: yaml

      policies:
         allowed_algorithms:
            - ^harbor2\.vantage6\.ai/[a-zA-Z]+/[a-zA-Z]+
            - ^harbor2\.vantage6\.ai/algorithms/glm$
            - ^harbor2\.vantage6\.ai/algorithms/glm@sha256:82becede498899ec668628e7cb0ad87b6e1c371cb8a1e597d83a47fac21d6af3$
         allowed_algorithm_stores:
            - https://store.cotopaxi.vantage6.ai

   These four examples lead to the following restrictions:
   1. ``^harbor2\.vantage6\.ai/[a-zA-Z]+/[a-zA-Z]+``: allow all images
      from the harbor2.vantage6.ai registry
   2. ``^harbor2\.vantage6\.ai/algorithms/glm$``: only allow the GLM image, but
      all builds of this image
   3. ``^harbor2\.vantage6\.ai/algorithms/glm@sha256:82becede498899ec668628e7cb0ad87b6e1c371cb8``
      ``a1e597d83a47fac21d6af3$``: allows only this specific build from the GLM
      image to run on your data
   4. ``https://store.cotopaxi.vantage6.ai``: allow all algorithms from the
      cotopaxi algorithm store

   Note that you can also define regular expressions for the algorithm stores, and that
   you can combine the two policies. The section :ref:`node-configure-algorithm-access`
   below explains the considerations you need to take into account when setting these
   policies.

-  Enable ``DOCKER_CONTENT_TRUST`` to verify the origin of the image.
   For more details see the `documentation from
   Docker <https://docs.docker.com/engine/security/trust/>`__.

.. warning::
    By enabling ``DOCKER_CONTENT_TRUST`` you might not be able to use
    certain algorithms. You can check this by verifying that the images you want
    to be used are signed.

.. _node-configure-algorithm-access:

Configuring algorithm access to the data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As explained above, you can :ref:`specify a list <node-configure-security>` of
allowed algorithms in the configuration file of the data station. Only algorithms
specified on that list, by providing the names of the Docker images of these algorithms,
are allowed to run on the data station. Also, you can specify the exact (non-forgeable)
hash (i.e. version) of the trusted algorithm. Note that this process requires manual
updates to the data station configuration, as well as a data station restart,
each time that a new algorithm is approved or an existing algorithm is updated.

It is also possible to allow a set of algorithms at once by providing a pattern, i.e.
a regular expression. This makes it e.g. possible to allow a certain
directory with algorithms. The disadvantage of this approach is that if an
attacker (or IT personnel with malintent) manages to get access to that
directory, a malicious algorithm that would be put there, would pass the filter
of allowed algorithms. Similarly, specifying single algorithms without hashes
would not be fully secure if an attacker can access that address.

A third possibility is to allow algorithms from a trusted algorithm store. The
benefit of this is that the algorithm store already manages the algorithms
currently allowed including most up-to-date version information. When the
algorithm is updated, the store will tell the node automatically to only allow
the new version. The disadvantage of this approach is that if an attacker gains
access to the store, the node is not protected from malicious algorithms.

The safest policy regarding allowed algorithms is to specify an exact list of
all allowed algorithms, including the version (specified by the image hash), at
the node. However, this also entails a significant maintenance burden if the
algorithms are updated frequently. Institutes following this policy would have to log in
to their data station for every algorithm change to update the allowed algorithm
configuration. Although this is a quick update, it would still require a manual
action every time. Also, as a manual action, it is error prone. Errors will probably
prevent the algorithm from running successfully on that node. Alternatively, manual
errors may lead to security concerns, but this is less likely.

If your project has a separate algorithm store and image registry, a good alternative is
to define two policies at the node, that ascertain
restrictions on both the algorithm store and the registry. One policy defines
that only algorithms from the projects's own algorithm store are allowed and the
other policy only allows algorithms from the project's own image registry. That way,
an attacker would need to gain access to both the private registry, the algorithm store
and the server before being able to send a malicious task. The probability of a
successful attack on all of these components is much lower than a successful attack on
a single component.

.. _node-logging:

Logging
"""""""

To configure the logger, look at the logging section
in the example configuration file in :ref:`node-configure-structure`.

Useful commands:

1. ``v6 node files``: shows you where the log file is stored
2. ``v6 node attach``: shows live logs of a running server in your current
   console. This can also be achieved when starting the node with
   ``v6 node start --attach``
