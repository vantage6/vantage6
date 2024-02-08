.. _algorithm-store-configure:

Configure
---------

The algorithm store requires a configuration file to run. This is a
``yaml`` file with a specific format.

The next sections describes how to configure the algorithm store. It first provides a few
quick answers on setting up your store, then shows an example of all
configuration file options, and finally explains where your configuration files
are stored.

How to create a configuration file
""""""""""""""""""""""""""""""""""

The easiest way to create an initial configuration file is via:
``v6 algorithm-store new``. This allows you to configure the
basic settings. For more advanced configuration options, which are listed below,
you can view the :ref:`example configuration file <algorithm-store-config-file-structure>`.


Where is my configuration file?
"""""""""""""""""""""""""""""""

To see where your configuration file is located, you can use the following
command

.. code:: bash

    v6 algorithm-store files

.. warning::
    This command will only work for if the algorithm store has been deployed
    using the ``v6`` commands.

    Also, note that on local deployments you may need to specify the
    ``--user`` flag if you put your configuration file in the
    :ref:`user folder <algorithm-store-configure-location>`.

You can also create and edit this file manually.

.. _algorithm-store-config-file-structure:

All configuration options
"""""""""""""""""""""""""

The following configuration file is an example that intends to list all possible
configuration options.

You can download this file here: :download:`algorithm_store_config.yaml <yaml/algorithm_store_config.yaml>`

.. _algorithm-store-configuration-file:

.. literalinclude :: yaml/algorithm_store_config.yaml
    :language: yaml

.. todo this section is close duplicate of docs/node/configure -- merge?

.. _algorithm-store-configure-location:

Configuration file location
"""""""""""""""""""""""""""

The directory where to store the configuration file depends on your
operating system (OS). It is possible to store the configuration file at
**system** or at **user** level. At the user level, configuration files are only
available for your user. By default, algorithm store configuration files are
stored at **system** level.

The default directories per OS are as follows:

+---------+----------------------------+------------------------------------+
| **OS**  | **System**                 | **User**                           |
+=========+============================+====================================+
| Windows | |win_sys|                  | |win_usr|                          |
+---------+----------------------------+------------------------------------+
| MacOS   | |mac_sys|                  | |mac_usr|                          |
+---------+----------------------------+------------------------------------+
| Linux   | |lin_sys|                  | |lin_usr|                          |
+---------+----------------------------+------------------------------------+

.. |win_sys| replace:: ``C:\ProgramData\vantage\algorithm-store``
.. |win_usr| replace:: ``C:\Users\<user>\AppData\Local\vantage\algorithm-store``
.. |mac_sys| replace:: ``/Library/Application/Support/vantage6/algorithm-store``
.. |mac_usr| replace:: ``/Users/<user>/Library/Application Support/vantage6/algorithm-store``
.. |lin_sys| replace:: ``/etc/xdg/vantage6/algorithm-store/``
.. |lin_usr| replace:: ``/home/<user>/.config/vantage6/algorithm-store/``

.. warning::
    The command ``v6 algorithm-store`` looks in certain directories by default. It is
    possible to use any directory and specify the location with the ``--config``
    flag. However, note that using a different directory requires you to specify
    the ``--config`` flag every time!

    Similarly, you can put your algorithm store configuration file in the user folder
    by using the ``--user`` flag. Note that in that case, you have to specify
    the ``--user`` flag for all ``v6 algorithm-store`` commands.

.. _algorithm-store-logging:

Logging
"""""""

Logging is enabled by default. To configure the logger, look at the ``logging``
section in the example configuration in :ref:`algorithm-store-config-file-structure`.

Useful commands:

1. ``v6 algorithm-store files``: shows you where the log file is stored
2. ``v6 algorithm-store attach``: show live logs of a running store in your
   current console. This can also be achieved when starting the store
   with ``v6 algorithm-store start --attach``
