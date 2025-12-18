.. _smtp-server:

Mailserver
===========

Some features of the vantage6 hub use an SMTP server to send emails. For example,
the authentication service can send an email to a user when they lost their password, or
the algorithm store can send an email to alert someone that an algorithm review is
requested from them.

You need to set up the SMTP server yourself.
There are mhq-config-file-structureerver, and we will not go into detail here.
Just remember that you need to configure the vantage6 hub to use your SMTP server
(see :ref:`hq-config-file-structure`).
