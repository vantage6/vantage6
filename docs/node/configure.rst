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
configuration file is via: ``vnode new``. This allows you to configure the
basic settings. For more advanced configuration options, which are listed below,
you can view the :ref:`example configuration file <node-configure-structure>`.

Where is my configuration file?
"""""""""""""""""""""""""""""""

To see where your configuration file is located, you can use the following
command

.. code:: bash

    vnode files

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

.. note::
    Before version 4.0, we used `DTAP for key environments <https://en.wikipedia.org/wiki/Development,_testing,_acceptance_and_production>`__.
    One of these keys had to be provided at the highest level in the
    configuration file. From version 4.0 onwards, this key is no longer allowed.

    The deprecated environments in short:

    - ``dev``: Development environment. It is ok to break things here
    - ``test``: Testing environment. Here, you can verify that everything
      works as expected. This environment should resemble the target
      environment where the final solution will be deployed as much as
      possible.
    - ``acc``: Acceptance environment. If the tests were successful, you can
      try this environment, where the final user will test his/her analysis
      to verify if everything meets his/her expectations.
    - ``prod``: Production environment. The version of the proposed solution
      where the final analyses are executed.

    Before v4.0, you can also specify the key ``application`` if you do not
    want to specify one of the environments.

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
    The command ``vnode`` looks in these directories by default. However, it is
    possible to use any directory and specify the location with the ``--config``
    flag. But note that doing that requires you to specify the ``--config``
    flag every time you execute a ``vnode`` command!

    Similarly, you can put your node configuration file in the system folder
    by using the ``--system`` flag. Note that in that case, you have to specify
    the ``--system`` flag for all ``vnode`` commands.

Security
""""""""

As a data owner it is important that you take the necessary steps to
protect your data. Vantage6 allows algorithms to run on your data and
share the results with other parties. It is important that you review
the algorithms before allowing them to run on your data.

Once you approved the algorithm, it is important that you can verify
that the approved algorithm is the algorithm that runs on your data.
There are two important steps to be taken to accomplish this:

-  Set the (optional) ``allowed_images`` option in the
   node-configuration file. You can specify a list of regex expressions here.
   Some examples of what you could define:

   1. ``^harbor2.vantage6.ai/[a-zA-Z]+/[a-zA-Z]+``: allow all images
      from the vantage6 registry
   2. ``^harbor2.vantage6.ai/algorithms/glm``: only allow the GLM image, but
      all builds of this image
   3. ``^harbor2.vantage6.ai/algorithms/glm@sha256:82becede498899ec668628e7cb0ad87b6e1c371cb8``
      ``a1e597d83a47fac21d6af3``: allows only this specific build from the GLM
      image to run on your data

-  Enable ``DOCKER_CONTENT_TRUST`` to verify the origin of the image.
   For more details see the `documentation from
   Docker <https://docs.docker.com/engine/security/trust/>`__.

.. warning::
    By enabling ``DOCKER_CONTENT_TRUST`` you might not be able to use
    certain algorithms. You can check this by verifying that the images you want
    to be used are signed.

.. _node-logging:

Logging
"""""""

To configure the logger, look at the logging section
in the example configuration file in :ref:`node-configure-structure`.

Useful commands:

1. ``vnode files``: shows you where the log file is stored
2. ``vnode attach``: shows live logs of a running server in your current
   console. This can also be achieved when starting the node with
   ``vnode start --attach``
