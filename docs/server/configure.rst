

.. _server-configure:

Configure
^^^^^^^^^

The vantage6-server requires a configuration file to run. This is a
``yaml`` file with a specific format.

The next sections describes how to configure the server. It first provides a few
quick answers on setting up your server, then shows an example of all
configuration file options, and finally explains where your vantage6
configuration files are stored.

How to create a configuration file
""""""""""""""""""""""""""""""""""

The easiest way to create an initial
configuration file is via: ``vserver new``. This allows you to configure the
basic settings. For more advanced configuration options, which are listed below,
you can view the :ref:`example configuration file <server-config-file-structure>`.


Where is my configuration file?
"""""""""""""""""""""""""""""""

To see where your configuration file is located, you can use the following
command

.. code:: bash

    vserver files

.. warning::
    This command will usually only work for local test deployments of the
    vantage6 server. If you have deployed the server on a remote server,
    this command will probably not work.

    Also, note that on local deployments you may need to specify the
    ``--user`` flag if you put your configuration file in the
    :ref:`user folder <server-configure-location>`.

You can create and edit this file
manually. To create an initial configuration file you can also use the
configuration wizard: ``vserver new``.

.. _server-config-file-structure:

All configuration options
"""""""""""""""""""""""""

The following configuration file is an example that intends to list all possible
configuration options.

You can download this file here: :download:`server_config.yaml <yaml/server_config.yaml>`

.. literalinclude :: yaml/server_config.yaml
    :language: yaml

.. todo this section is close duplicate of docs/node/configure -- merge?

.. _server-configure-location:

Configuration file location
"""""""""""""""""""""""""""

The directory where to store the configuration file depends on you
operating system (OS). It is possible to store the configuration file at
**system** or at **user** level. At the user level, configuration files are only
available for your user. By default, server configuration files are stored at
**system** level.

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

.. |win_sys| replace:: ``C:\ProgramData\vantage\server``
.. |win_usr| replace:: ``C:\Users\<user>\AppData\Local\vantage\server``
.. |mac_sys| replace:: ``/Library/Application/Support/vantage6/server``
.. |mac_usr| replace:: ``/Users/<user>/Library/Application Support/vantage6/server``
.. |lin_sys| replace:: ``/etc/xdg/vantage6/server/``
.. |lin_usr| replace:: ``/home/<user>/.config/vantage6/server/``

.. warning::
    The command ``vserver`` looks in certain directories by default. It is
    possible to use any directory and specify the location with the ``--config``
    flag. However, note that using a different directory requires you to specify
    the ``--config`` flag every time!

    Similarly, you can put your server configuration file in the user folder
    by using the ``--user`` flag. Note that in that case, you have to specify
    the ``--user`` flag for all ``vserver`` commands.

.. _server-logging:

Logging
"""""""

Logging is enabled by default. To configure the logger, look at the ``logging``
section in the example configuration in :ref:`server-config-file-structure`.

Useful commands:

1. ``vserver files``: shows you where the log file is stored
2. ``vserver attach``: show live logs of a running server in your
   current console. This can also be achieved when starting the server
   with ``vserver start --attach``
