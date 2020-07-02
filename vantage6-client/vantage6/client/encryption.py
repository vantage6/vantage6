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
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key
)

from vantage6.common import (
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

    @staticmethod
    def bytes_to_str(data: bytes) -> str:
        """Encode bytes as base64 encoded string."""
        return bytes_to_base64s(data)

    @staticmethod
    def str_to_bytes(data: str) -> bytes:
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
        """ Load a private key file into this instance."""

        if not private_key_file.exists():
            raise FileNotFoundError(
                f"Private key file {private_key_file} not found.")

        self.log.debug("Loading private key")

        return load_pem_private_key(
            private_key_file.read_bytes(),
            password=None,
            backend=default_backend()
        )

    @staticmethod
    def create_new_rsa_key(path: Path):
        """ Creates a new RSA key for E2EE.
        """
        private_key = rsa.generate_private_key(
            backend=default_backend(),
            key_size=4096,
            public_exponent=65537
        )

        path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            )
        )
        return private_key

    @property
    def public_key_bytes(self):
        """ Returns the public key bytes from the organization."""
        return self.create_public_key_bytes(self.private_key)

    @staticmethod
    def create_public_key_bytes(private_key):
        return private_key.public_key().public_bytes(
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
