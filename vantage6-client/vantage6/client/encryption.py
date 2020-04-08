""" Encryption between organizations

Module to provide async encrpytion between organizations. All input and
result fields should be encrypted when communicating to the central
server.

All incomming messages (input/results) should be encrypted using the
public key of this organization. This way we can decrypt them using our
private key.

In the case we are sending messages (input/results) we need to encrypt
it using the public key of the receiving organization. (retreiving
these public keys is outside the scope of this module).

TODO handle no public key from other organization (should that happen here)
"""
import os
import logging

from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key
)

from vantage6.client.constants import APPNAME
from vantage6.client.util import (
    Singleton,
    logger_name,
    bytes_to_base64s,
    base64s_to_bytes
)

SEPARATOR = '$'

# ------------------------------------------------------------------------------
# CryptorBase
# ------------------------------------------------------------------------------
class CryptorBase(metaclass=Singleton):
    """Base class/interface for encryption implementations."""
    def __init__(self):
        """Create a new CryptorBase instance."""
        self.log = logging.getLogger(logger_name(__name__))

    def bytes_to_str(self, data: bytes) -> str:
        """Encode bytes as base64 encoded string."""
        return bytes_to_base64s(data)

    def str_to_bytes(self, data: str) -> bytes:
        """Decode base64 encoded string to bytes."""
        return base64s_to_bytes(data)


    def encrypt_bytes_to_str(self, data: bytes, pubkey_base64: str) -> str:
        """Encrypt bytes in `data` using a (base64 encoded) public key."""
        return self.bytes_to_str(data)

    def decrypt_str_to_bytes(self, data: str) -> bytes:
        """Decrypt base64 encoded *string* `data."""
        return self.str_to_bytes(data)


# ------------------------------------------------------------------------------
# DummyCryptor
# ------------------------------------------------------------------------------
class DummyCryptor(CryptorBase):
    """Does absolutely nothing."""
    pass


# ------------------------------------------------------------------------------
# RSACryptor
# ------------------------------------------------------------------------------
class RSACryptor(CryptorBase):
    """Wrapper class for the cryptography package.

        It loads the private key, and has an interface to encrypt en decrypt
        messages. If no private key is found, it can generate one, and store
        it at the default location. The encrpytion can be done via a public
        key from another organization, make sure the key is in the right
        data-type.

        Communication between node and server requires serialization (and
        deserialization) of the encrypted messages (which are in bytes).
        The API can not communicate bytes, therefore a base64 conversion
        needs to be executed (and also a utf-8 encoding needs to be applied
        because of the way python implemented base64). The same goed for
        sending and receiving the public_key.
    """

    def __init__(self, private_key_file):
        """Create a new RSACryptor instance."""
        super().__init__()
        self.private_key = self.__load_private_key(private_key_file)

    def __load_private_key(self, private_key_file):
        """ Load a private key file into this instance.

            If `private_key_file` has not been supplied the default key
            is used (which is fine in most cases). In case the file
            does not exist it is generated, make sure python has access
            to the filepath in case you have specified one.

            :param private_key_file: path to a private key file (or
                where you want to store one)

            TODO consider making this a static function
        """
        # FIXME: __load_private_key() should not generate a new key; this is an
        #   unexpected side effect given the name of the method. Either rename
        #   the function or refactor to generate the key if this function
        #   cannot find/load it.
        if not private_key_file.exists():
            self.log.warning(
                f"Private key file {private_key_file} not found. Now generating one. "
                f"This is could be normal if you run {APPNAME} for the first "
                f"time."
            )
            self.__create_new_rsa_key(private_key_file)

        self.log.debug("Loading private key")

        return load_pem_private_key(
            private_key_file.read_bytes(),
            password=None,
            backend=default_backend()
        )

    def __create_new_rsa_key(self, path: Path):
        """ Creates a new RSA key for E2EE.
        """
        self.log.info(f"Generating RSA-key at {path}")
        private_key = rsa.generate_private_key(
            backend=default_backend(),
            key_size=4096,
            public_exponent=65537
        ).private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        path.write_bytes(private_key)

    @property
    def public_key_bytes(self):
        """ Returns the public key bytes from the organization."""
        return self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    @property
    def public_key_str(self):
        """ Returns a JSON safe public key, used for the API."""
        return bytes_to_base64s(self.public_key_bytes)

    def encrypt_bytes_to_str(self, data: bytes, pubkey_base64s: str) -> str:
        """Encrypt bytes in `data` using a (base64 encoded) public key."""

        # Use the shared key for symmetric encryption/decryption of the payload
        shared_key = os.urandom(32)
        iv_bytes = os.urandom(16)

        cipher = Cipher(
            algorithms.AES(shared_key),
            modes.CTR(iv_bytes),
            backend=default_backend()
        )

        encryptor = cipher.encryptor()
        encrypted_msg_bytes = encryptor.update(data) + encryptor.finalize()

        # Create a public key instance.
        pubkey = load_pem_public_key(
            base64s_to_bytes(pubkey_base64s),
            backend=default_backend()
        )

        encrypted_key_bytes = pubkey.encrypt(
            shared_key,
            padding.PKCS1v15()
        )

        encrypted_key = self.bytes_to_str(encrypted_key_bytes)
        iv = self.bytes_to_str(iv_bytes)
        encrypted_msg = self.bytes_to_str(encrypted_msg_bytes)

        return SEPARATOR.join([encrypted_key, iv, encrypted_msg])


    def decrypt_str_to_bytes(self, data: str) -> bytes:
        """Decrypt base64 encoded *string* `data."""

        (encrypted_key, iv, encrypted_msg) = data.split(SEPARATOR)

        # Yes, this can be done more efficiently.
        encrypted_key_bytes = self.str_to_bytes(encrypted_key)
        iv_bytes = self.str_to_bytes(iv)
        encrypted_msg_bytes = self.str_to_bytes(encrypted_msg)

        # Decrypt the shared key using asymmetric encryption
        shared_key = self.private_key.decrypt(
            encrypted_key_bytes,
            padding.PKCS1v15()
        )

        self.log.info(f'Decrypted shared key: {shared_key}')

        # Use the shared key for symmetric encryption/decryption of the payload
        cipher = Cipher(
            algorithms.AES(shared_key),
            modes.CTR(iv_bytes),
            backend=default_backend()
        )

        decryptor = cipher.decryptor()
        result = decryptor.update(encrypted_msg_bytes) + decryptor.finalize()

        return result


    def verify_public_key(self, pubkey_base64) -> bool:
        """Verifies the public key.

            Compare a public key with the generated public key from
            the private key that is stored in this instance. This is
            usefull for verifying that the public key stored on the
            server is derived from the currently used private key.

            :param pubkey_base64: public_key as returned from the
                server (still base64 encoded)
        """
        public_key_server = base64s_to_bytes(pubkey_base64)
        return self.public_key_bytes == public_key_server


#    def encrypt_bytes_to_base64s(self, msg: bytes, public_key_base64: str) -> str:
#        """Encrypt bytes in `msg` into a base64 encoded string.
#
#            :param msg: message to be encrypted
#            :param public_key_base64: public key base64 decoded
#                (directly from API transport)
#
#            TODO we should retrieve all keys once... and store them in
#                the node
#        """
#        # unpack public key
#        public_key_bytes = base64s_to_bytes(public_key_base64)
#
#        # encrypt message using public key
#        encrypted_msg = self.encrypt(msg, public_key_bytes)
#
#        # prepare message for transport
#        base64_str = bytes_to_base64s(encrypted_msg)
#
#        return base64_str
#
#    def decrypt_bytes_from_base64(self, msg: str) -> bytes:
        """Decrypt base64 encoded *string* `msg` using our private key.

            :param msg: string utf-8 encoded base64 encrypted msg
        """
        msg_bytes = base64s_to_bytes(msg)
        return self._decrypt_bytes(msg_bytes)
#


#class NoCryptor(Cryptor):
#    """ When the collaboration of which the node part is is unencrypted.
#
#        This overwrites all encryption / descryption methods to not
#        use encryption, but does cenvert between str and bytes if needed
#    """
#    def __init__(self, private_key_file=None):
#       # super().__init__(private_key_file=private_key_file)
#       self.log = logging.getLogger(logger_name(__name__))
#       self.log.warning(
#               "Encrpytion disabled! Use this only for debugging")
#
#    def encrypt_bytes_to_base64s(
#        self, msg: bytes, public_key_base64: str) -> str:
#        return bytes_to_base64s(msg)
#
#    def encrypt_bytes(self, msg: bytes, public_key_bytes: bytes) -> bytes:
#       return msg
#
#    def decrypt_bytes(self, msg: bytes) -> bytes:
#       return msg
#
#    def decrypt_bytes_from_base64(self, msg: str) -> bytes:
#       return base64s_to_bytes(msg)
#
#
