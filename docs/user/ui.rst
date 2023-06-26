.. _ui:

User interface
--------------

The User Interface (UI) is a website where you can login with your vantage6
user account. Which website this is, depends on the vantage6 server you are
using. If you are using the Petronas server, go to
https://portal.petronas.vantage6.ai and login with your user account.

Using the UI should be relatively straightforward. There are buttons
that should help you e.g. create a task or change your password. If
anything is unclear, please contact us via
`Discord <https://discord.com/invite/yAyFf6Y>`__.

.. figure:: /images/ui-screenshot.png

    Screenshot of the vantage6 UI

.. note::
    If you are a server administrator and want to set up a user interface, see
    :ref:`this section <install-ui>` on deploying a UI.

.. note::
    If you are :ref:`running your own server <use-server>` with ``vserver start``,
    you can start the UI locally with ``vserver start --with-ui``, or you may
    specify that the UI should always be started in the ``ui`` section of the
    :ref:`server configuration file <server-configuration-file>`.