Two-factor authentication
-------------------------

*Available since version 3.5.0*

The vantage6 infrastructure includes the option to use two-factor
authentication (2FA). This option is set at the server level: the server administrator
decides if it is either enabled or disabled for everyone. Users cannot set this
themselves. Server administrators can choose to require 2FA when
prompted in ``v6 server new``, or by adding the option
``two_factor_auth: true`` to the configuration file (see :ref:`server-configure`).

Currently, the only 2FA option is to use
`Time-based one-time passwords (TOTP) <https://www.twilio.com/docs/glossary/totp>`_
With this form of 2FA, you use your phone to scan a QR code using an authenticator
app like LastPass authenticator or Google authenticator. When you scan the QR
code, your vantage6 account is added to the authenticator app and will show you
a 6-digit code that changes every 30 seconds.

Setting up 2FA for a user
+++++++++++++++++++++++++

If a new user logs in, or if a user logs in for the first time after a server
administrator has enabled 2FA, they will be required to set it up. The endpoint ``/token/user`` will first verify
that their password is correct, and then set up 2FA. It does so by generating
a random `TOTP <https://www.twilio.com/docs/glossary/totp>`_ secret for the
user, which is stored in the database. From this secret, a URI is generated that
can be used to visualize the QR code.

If the user is logging in via the vantage6 user interface, this QR code will be
visualized to allow the user to scan it. Also, users that login via the Python
client will be shown a QR code. In both cases, they also have the option to
manually enter the TOTP secret into their authenticator app, in case scanning
the QR code is not possible.

Users that log in via the R client or directly via the API will have to
visualize the QR code themselves, or manually enter the TOTP secret into their
authenticator app.

Using 2FA
+++++++++

If a user has already setup 2FA tries to login, the endpoint ``/token/user``
will require that they provide their 6-digit TOTP code via the ``mfa_code``
argument. This code will be checked using the TOTP secret stored in the database,
and if it is valid, the user will be logged in.

To prevent users with a slow connection from having difficulty logging in,
valid codes from the 30s period directly prior to the current period will also
be logged in.

Resetting 2FA
+++++++++++++

When a user loses access to their 2FA, they may reset it via their email. They
should use the endpoint ``/recover/2fa/lost`` to get an email with a reset token
and then use the reset token in ``/recover/2fa/reset`` to reset 2FA. This
endpoint will give them a new QR code that they can visualize just like the
initial QR code.