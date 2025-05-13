End to end encryption
---------------------

Encryption in vantage6 is handled at organization level. Whether
encryption is used or not, is set at collaboration level. All the nodes
in the collaboration need to agree on this setting. You can enable or
disable encryption in the node configuration file, see the example in
:ref:`node-configure-structure`.

.. figure:: /images/encryption.png

   Encryption takes place between organizations therefore all nodes and
   users from the a single organization should use the same private key.

The encryption module encrypts data so that the server is unable to read
communication between users and nodes. The only messages that go from
one organization to another through the server are computation requests
and their results. Only the algorithm input and output are encrypted.
Other metadata (e.g. time started, finished, etc), can be read by the
server.

The encryption module uses RSA keys. The public key is uploaded to the
vantage6 server. Tasks and other users can use this public key (this is
automatically handled by the python-client and R-client) to send
messages to the other parties.

.. note::
    The RSA key is used to create a shared secret which is used for encryption
    and decryption of the payload.

When the node starts, it checks that the public key stored at the server
is derived from the local private key. If this is not the case, the node
will replace the public key at the server.

.. warning::
    If an organization has multiple nodes and/or users, they must use the same
    private key.

To create a new keypair, you can use the command ``v6 node create-private-key``.
This will create the keypair and share the public key with the server. The private key
is stored locally. If a private key already exists locally, the existing key is reused
(unless you use the ``--force`` flag). This way, it is easy to configure multiple nodes
to use the same key.

It is also possible to generate the keypair yourself and upload the public key yourself
via UI, Python client, or REST API.

.. warning::

    We recommend to always create a new keypair for use within vantage6, and not use
    an existing keypair that you use for other purposes. This way, an attacker that
    steals your private key elsewhere cannot use it to decrypt data in vantage6 and
    *vice versa*.