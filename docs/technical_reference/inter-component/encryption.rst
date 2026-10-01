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

The encryption module encrypts data so that HQ is unable to read
communication between users and nodes. The only messages that go from
one organization to another through HQ are computation requests
and their results. Only the algorithm input and output are encrypted.
Other metadata (e.g. time started, finished, etc), can be read by HQ.

The encryption module uses RSA keys. The public key is uploaded to the
vantage6 HQ. Tasks and other users can use this public key (this is
automatically handled by the Python client) to send
messages to the other parties.

.. note::
    The RSA key is used to create a shared secret which is used for encryption
    and decryption of the payload.

When the node starts, it checks that the public key stored at HQ
is derived from its private key. If HQ has no public key for the organization yet, the
node uploads it. If HQ has a different public key, the node refuses to start rather than
replacing it, as that would break decryption for the organization's other nodes and
users.

.. warning::
    If an organization has multiple nodes and/or users, they must use the same
    private key.

To create a new keypair, you can use the command ``v6 node create-private-key``.
This will create the keypair and share the public key with HQ. The private key is
stored in a Kubernetes secret (``<node release name>-private-key``) in the namespace of
the node, which is mounted into the node when it starts. No private key file is written
to disk. If the secret already exists, the existing key is reused (unless you use the
``--overwrite`` flag). ``v6 node new`` offers to create the key when you enable
encryption.

If your organization already has a public key at HQ, a new key is not generated: store
the organization's existing private key with ``--from-file`` instead (``v6 node new``
asks for it). Replacing the organization's keypair requires
``--replace-organization-key``.

The secret is kept when the node is stopped or restarted, and is deleted when the node
is removed with ``v6 node remove``.

To use an existing private key, store it with
``v6 node create-private-key --from-file <path to private key>``.

.. warning::

    We recommend to always create a new keypair for use within vantage6, and not use
    an existing keypair that you use for other purposes. This way, an attacker that
    steals your private key elsewhere cannot use it to decrypt data in vantage6 and
    *vice versa*.