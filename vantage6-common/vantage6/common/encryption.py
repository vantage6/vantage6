"""Encryption between organizations

Module to provide async encrpytion between organizations. All input and
result fields should be encrypted when communicating to the central
server.

All incomming messages (input/results) should be encrypted using the
public key of this organization. This way we can decrypt them using our
private key.

In the case we are sending messages (input/results) we need to encrypt
it using the public key of the receiving organization. (retreiving
these public keys is outside the scope of this module).
"""

# TODO handle no public key from other organization (should that happen here?)
import os
import logging
import base64
import json
from typing import IO

from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key,
)

from vantage6.common import Singleton, logger_name, bytes_to_base64s, base64s_to_bytes
from vantage6.common.globals import DEFAULT_CHUNK_SIZE, STRING_ENCODING

SEPARATOR = "$"
SHARED_ENCRYPT_KEY_LENGTH = 32
IV_LENGTH = 16


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
        """
        Encode bytes as base64 encoded string.

        Parameters
        ----------
        data: bytes
            The data to encode.

        Returns
        -------
        str
            The base64 encoded string.
        """
        return bytes_to_base64s(data)

    @staticmethod
    def str_to_bytes(data: str) -> bytes:
        """
        Decode base64 encoded string to bytes.

        Parameters
        ----------
        data: str
            The base64 encoded string.

        Returns
        -------
        bytes
            The encoded string converted to bytes.
        """
        return base64s_to_bytes(data)

    def encrypt_bytes_to_str(
        self, data: bytes, pubkey_base64: str, skip_base64_encoding_of_msg: bool = False
    ) -> str:
        """
        Encrypt bytes in `data` using a (base64 encoded) public key.

        Note that the public key is ignored in this base class. If you want
        to encode your data with a public key, use the `RSACryptor` class.

        Parameters
        ----------
        data: bytes
            The data to encrypt.
        pubkey_base64: str
            The public key to use for encryption. This is ignored in this
            base class.
        skip_base64_encoding_of_msg: bool
            If True, the encrypted message will not be base64 encoded.
            This is useful when the data is already in bytes format and
            does not need further encoding (e.g., when uploading to blob storage).

        Returns
        -------
        str
            The encrypted data encoded as base64 string.
        """
        return self.bytes_to_str(data)

    def decrypt(self, data: str | bytes) -> bytes:
        """
        Decrypt base64 encoded *string* data.

        Parameters
        ----------
        data: str | bytes
            The data to decrypt. Can be either a
            string or bytes, depending on whether
            the data comes from blob storage or not.

        Returns
        -------
        bytes
            The decrypted data.
        """
        # If the data comes from blob storage, decode it to a string first.
        if isinstance(data, bytes):
            return self.str_to_bytes(data.decode(STRING_ENCODING))
        elif isinstance(data, str):
            return self.str_to_bytes(data)
        else:
            raise ValueError(
                "Data passed for decryption must be either a string or bytes."
            )

    def encrypt_stream(
        self,
        stream: IO[bytes],
        pubkey_base64s: str = None,
        chunk_size=DEFAULT_CHUNK_SIZE,
    ):
        """
        Base64-encode a stream, yielding encoded chunks.
        Naming here is confusing (this function does not encrypt),
        but it is kept for compatibility with the `RSACryptor` class,
        as well as staying consistent with existing cryptorbase method
        names like `encrypt_bytes_to_str`.

        Parameters
        ----------
        stream : file-like
            The input stream to encode (must support .read()).
        pubkey_base64s : str
            Ignored. Only used in `RSACryptor` for encryption.
        chunk_size : int
            The size of chunks to read and encode.

        Yields
        ------
        bytes
            Base64-encoded data chunks.
        """

        buffer = b""
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            buffer += chunk
            # Only encode in multiples of 3 (base64 works on 3-byte blocks)
            to_encode_len = (len(buffer) // 3) * 3
            if to_encode_len == 0:
                continue
            to_encode = buffer[:to_encode_len]
            buffer = buffer[to_encode_len:]
            encoded = base64.b64encode(to_encode)
            yield encoded
        # Encode any remaining data in the buffer
        if buffer:
            encoded = base64.b64encode(buffer)
            yield encoded

    def decrypt_stream(self, stream, chunk_size=DEFAULT_CHUNK_SIZE):
        """
        Decode a base64-encoded stream to bytes, yielding decoded chunks.
        Naming here is confusing (this function does not decrypt),
        but it is kept for compatibility with the `RSACryptor` class,
        as well as staying consistent with existing cryptorbase method
        names like `decrypt_str_to_bytes`.

        Parameters
        ----------
        stream : file-like
            The input stream to decode (must support .read()).
        chunk_size : int
            The size of chunks to read and decode.

        Yields
        ------
        bytes
            Decoded data chunks.
        """

        # Read the entire stream (since base64 decoding requires the full input)
        buffer = b""
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            buffer += chunk
            # Only decode in multiples of 4
            to_decode_len = (len(buffer) // 4) * 4
            if to_decode_len == 0:
                continue
            to_decode = buffer[:to_decode_len]
            buffer = buffer[to_decode_len:]
            decoded = base64.b64decode(to_decode)
            yield decoded
        # Decode any remaining data in the buffer
        if buffer:
            # Pad buffer to a multiple of 4 for base64 decoding.
            # The '=' padding is ignored by the base64 decoder and only serves to
            # ensure the input length is valid for decoding.
            padding_len = (-len(buffer)) % 4
            if padding_len:
                buffer += b"=" * padding_len
            try:
                decoded = base64.b64decode(buffer)
                yield decoded
            except Exception as e:
                self.log.error(f"Failed to decode base64 buffer: {e}")
                raise


# ------------------------------------------------------------------------------
# DummyCryptor
# ------------------------------------------------------------------------------
class DummyCryptor(CryptorBase):
    """Does absolutely nothing to encrypt the data."""


# ------------------------------------------------------------------------------
# RSACryptor
# ------------------------------------------------------------------------------
class RSACryptor(CryptorBase):
    """
    Wrapper class for the cryptography package.

    It loads the private key, and has an interface to encrypt en decrypt
    messages. If no private key is found, it can generate one, and store
    it at the default location. The encrpytion can be done via a public
    key from another organization, make sure the key is in the right
    data-type.

    Communication between node and server requires serialization (and
    deserialization) of the encrypted messages (which are in bytes).
    The API can not communicate bytes, therefore a base64 conversion
    needs to be executed (and also a utf-8 encoding needs to be applied
    because of the way python implemented base64). The same goes for
    sending and receiving the public_key.

    Parameters
    ----------
    private_key_file: Path
        The path to the private key file.
    """

    def __init__(self, private_key_file: Path) -> None:
        """
        Create a new RSACryptor instance.

        Parameters
        ----------
        private_key_file: Path
            The path to the private key file.
        """
        super().__init__()
        self.private_key = self.__load_private_key(private_key_file)

    def __load_private_key(self, private_key_file: Path) -> PrivateKeyTypes:
        """
        Load a private key file into this instance.

        Parameters
        ----------
        private_key_file: Path
            The path to the private key file.

        Returns
        -------
        Any
            The loaded private key.

        Raises
        ------
        FileNotFoundError
            If the private key file does not exist.
        """

        if not private_key_file.exists():
            raise FileNotFoundError(f"Private key file {private_key_file} not found.")

        self.log.debug("Loading private key")

        return load_pem_private_key(
            private_key_file.read_bytes(), password=None, backend=default_backend()
        )

    def _parse_header(self, header: bytes | str) -> tuple:
        """
        Parse header to extract encrypted_key, iv, and the encrypted message.

        Parameters
        ----------
        header : str
            The header to parse. Should contain three parts separated by the SEPARATOR.

        Returns
        -------
        tuple
            Tuple containing:
            - encrypted_key_b64 (str): base64 encoded encrypted AES key
            - iv_b64 (str): base64 encoded initialization vector
            - encrypted_msg (str): base64 encoded or raw encrypted message
        """
        header_str = header
        parts = header_str.split(SEPARATOR, 2)
        if len(parts) != 3:
            raise ValueError(
                "Header format is invalid — expected three parts separated by '$'."
            )
        return parts

    def _decode_shared_key(self, encrypted_key_bytes: bytes) -> bytes:
        """
        Decrypt and decode the shared AES key.

        Parameters
        ----------
        encrypted_key_bytes : bytes
            The encrypted AES key as bytes, typically extracted from the header.

        Returns
        -------
        bytes
            The decrypted AES key (should be 32 bytes for AES-256).
        """
        # Decrypt the shared key using asymmetric encryption
        shared_key = self.private_key.decrypt(encrypted_key_bytes, padding.PKCS1v15())
        # In the UI, the bytes have to be base64 encoded before encryption (we cannot
        # encrypt bytes directly in javascript) - so if this key was encrypted in the
        # UI, we need to decode it here as extra step. If it fails, ignore it as it is
        # apparently not needed.
        # TODO v5+ add additional encoding step in Python so that we always have the
        # same process
        try:
            shared_key = self.str_to_bytes(shared_key.decode(STRING_ENCODING))
        except UnicodeDecodeError:
            pass
        if len(shared_key) != SHARED_ENCRYPT_KEY_LENGTH:
            raise ValueError(
                f"Decrypted AES key length is {len(shared_key)} bytes, expected 32 bytes for AES-256."
            )
        return shared_key

    def _aes_ctr_decrypt(
        self, encrypted_msg_bytes: bytes, shared_key: bytes, iv_bytes: bytes
    ) -> bytes:
        """
        Decrypt bytes using AES-CTR mode.

        Parameters
        ----------
        encrypted_msg_bytes : bytes
            The encrypted message bytes to decrypt.
        shared_key : bytes
            The AES key to use for decryption (must be 32 bytes for AES-256).
        iv_bytes : bytes
            The initialization vector for AES-CTR (must be 16 bytes).

        Returns
        -------
        bytes
            The decrypted message bytes.
        """
        cipher = self._create_aes_cipher(shared_key, iv_bytes)
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_msg_bytes) + decryptor.finalize()

    def _read_header_from_stream(self, stream) -> tuple:
        """
        Read and parse the header from a stream until two separators are found.

        Parameters
        ----------
        stream : file-like
            The input stream to read from (must support .read()).

        Returns
        -------
        tuple
            Tuple containing:
            - encrypted_key_b64 (str): base64 encoded encrypted AES key
            - iv_b64 (str): base64 encoded initialization vector
            - encrypted_msg (str): base64 encoded or raw encrypted message
        """
        sep_bytes = SEPARATOR.encode()
        header_bytes = b""
        # Read chunks until we find two separators
        # This is necessary to extract the encrypted key and IV.
        while header_bytes.count(sep_bytes) < 2:
            c = stream.read(1)
            if not c:
                raise RuntimeError("Stream ended before header was fully read")
            header_bytes += c
        header_str = header_bytes.decode(STRING_ENCODING)
        return self._parse_header(header_str)

    def _load_public_key(self, pubkey_base64s: str):
        """
        Load a PEM public key from a base64 string.

        Parameters
        ----------
        pubkey_base64s : str
            The public key in base64 string format.

        Returns
        -------
        public key object
            The loaded public key.

        Raises
        ------
        ValueError
            If the public key cannot be loaded.
        """
        try:
            return load_pem_public_key(
                self.str_to_bytes(pubkey_base64s), backend=default_backend()
            )
        except Exception as e:
            self.log.error(f"Failed to load public key: {e}")
            raise ValueError("Invalid public key provided for encryption.") from e

    def _create_aes_cipher(self, key: bytes, iv: bytes):
        """
        Create an AES cipher object in CTR mode.

        Parameters
        ----------
        key : bytes
            The AES key (must be 32 bytes for AES-256).
        iv : bytes
            The initialization vector (must be 16 bytes).

        Returns
        -------
        Cipher
            The AES cipher object.
        """
        return Cipher(algorithms.AES(key), modes.CTR(iv), backend=default_backend())

    @staticmethod
    def create_new_rsa_key(path: Path) -> rsa.RSAPrivateKey:
        """
        Creates a new RSA key for E2EE.

        Parameters
        ----------
        path: Path
            The path to the private key file.

        Returns
        -------
        RSAPrivateKey
            The newly created private key.
        """
        private_key = rsa.generate_private_key(
            backend=default_backend(), key_size=4096, public_exponent=65537
        )

        path.write_bytes(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        return private_key

    @property
    def public_key_bytes(self) -> bytes:
        """
        Returns the public key bytes from the organization.

        Returns
        -------
        bytes
            The public key as bytes.
        """
        return self.create_public_key_bytes(self.private_key)

    @staticmethod
    def create_public_key_bytes(private_key: rsa.RSAPrivateKey) -> bytes:
        """
        Create a public key from a private key.

        Parameters
        ----------
        private_key: RSAPrivateKey
            The private key to use.

        Returns
        -------
        bytes
            The public key as bytes.
        """
        return private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

    @property
    def public_key_str(self) -> str:
        """
        Returns a JSON safe public key, used for the API.

        Returns
        -------
        str
            The public key as base64 encoded string.
        """
        return bytes_to_base64s(self.public_key_bytes)

    def encrypt_bytes_to_str(
        self,
        data: bytes,
        pubkey_base64s: str,
        skip_base64_encoding_of_msg: bool = False,
    ) -> str | bytes:
        """
        Encrypt bytes in `data` using a (base64 encoded) public key.

        Parameters
        ----------
        data: bytes
            The data to encrypt.
        pubkey_base64s: str
            The public key to use for encryption.
        skip_base64_encoding_of_msg: bool
            If True, the encrypted message will not be base64 encoded.
            This is useful when the data is already in bytes format and
            does not need further encoding (e.g., when uploading to blob storage).

        Returns
        -------
        str
            The encrypted data encoded as base64 string.
        """

        # Use the shared key for symmetric encryption of the payload
        shared_key = os.urandom(SHARED_ENCRYPT_KEY_LENGTH)
        iv_bytes = os.urandom(IV_LENGTH)

        # encrypt the data symmetrically with the shared key. This is done because
        # symmetric encryption is faster than asymmetric encryption and results in a
        # smaller result.
        cipher = self._create_aes_cipher(shared_key, iv_bytes)
        encryptor = cipher.encryptor()
        encrypted_msg_bytes = encryptor.update(data) + encryptor.finalize()

        try:
            pubkey = self._load_public_key(pubkey_base64s)
        except Exception as e:
            self.log.error(f"Failed to load public key: {e}")
            raise ValueError("Invalid public key provided for encryption.") from e

        # Encrypt the shared key using the public key (i.e. assymmetrically)
        encrypted_key_bytes = pubkey.encrypt(shared_key, padding.PKCS1v15())

        # Join the encrypted key, iv and encrypted message into a single string
        encrypted_key = self.bytes_to_str(encrypted_key_bytes)
        iv = self.bytes_to_str(iv_bytes)
        if skip_base64_encoding_of_msg:
            header = f"{encrypted_key}{SEPARATOR}{iv}{SEPARATOR}".encode(
                STRING_ENCODING
            )
            return header + encrypted_msg_bytes
        else:
            encrypted_msg = self.bytes_to_str(encrypted_msg_bytes)
            return SEPARATOR.join([encrypted_key, iv, encrypted_msg])

    def decrypt(self, data: str | bytes) -> bytes:
        """
        Decrypt run data that was encrypted using hybrid RSA/AES encryption.

        Parameters
        ----------
        data: str | bytes
            The data to decrypt. Can be either a string or bytes,
            depending on whether the data comes from blob storage or not.

        Returns
        -------
        bytes
            The decrypted data.
        """
        if isinstance(data, bytes):
            return self.decrypt_bytes_blob_storage(data)
        elif isinstance(data, str):
            return self.decrypt_str_to_bytes(data)

    def decrypt_bytes_blob_storage(self, data: bytes) -> bytes:
        """
        Decrypt *bytes* data coming from blob storage.
        This function expects the data to be in the format:
        <encrypted_key>$<iv>$<encrypted_msg>

        where:
        - <encrypted_key> is the base64 encoded encrypted AES key,
        - <iv> is the base64 encoded initialization vector,
        - <encrypted_msg> is the encrypted message in raw bytes.

        Parameters
        ----------
        data: bytes
            The data to decrypt.

        Returns
        -------
        bytes
            The decrypted data.
        """
        # Similar to decrypt_str_to_bytes, find the separator in order to
        # split key, iv and encrypted message.
        sep_bytes = SEPARATOR.encode()
        first_sep = data.find(sep_bytes)
        if first_sep == -1:
            raise ValueError("Header format is invalid — missing first separator.")
        second_sep = data.find(sep_bytes, first_sep + 1)
        if second_sep == -1:
            raise ValueError("Header format is invalid — missing second separator.")
        header_bytes = data[: second_sep + 1]
        header_str = header_bytes.decode(STRING_ENCODING)
        encrypted_key_b64, iv_b64, _ = self._parse_header(header_str)
        encrypted_key_bytes = self.str_to_bytes(encrypted_key_b64)
        # Only decode iv and shared key, the encrypted message is already in bytes
        iv_bytes = self.str_to_bytes(iv_b64)
        shared_key = self._decode_shared_key(encrypted_key_bytes)
        body = data[second_sep + 1 :]
        return self._aes_ctr_decrypt(body, shared_key, iv_bytes)

    def decrypt_str_to_bytes(self, data: str) -> bytes:
        """
        Decrypt base64 encoded *string* data.

        Parameters
        ----------
        data: str
            The data to decrypt.
            This function expects the data to be in the format:
            <encrypted_key>$<iv>$<encrypted_msg>

            where:
            - <encrypted_key> is the base64 encoded encrypted AES key,
            - <iv> is the base64 encoded initialization vector,
            - <encrypted_msg> is the encrypted message in base64 encoded string.

        Returns
        -------
        bytes
            The decrypted data.
        """
        # Note that the decryption process is the reverse of the encryption process
        # in the function above
        encrypted_key, iv, encrypted_msg = self._parse_header(data)
        # Convert the strings to back to bytes
        encrypted_key_bytes = self.str_to_bytes(encrypted_key)
        iv_bytes = self.str_to_bytes(iv)
        encrypted_msg_bytes = self.str_to_bytes(encrypted_msg)
        shared_key = self._decode_shared_key(encrypted_key_bytes)
        result = self._aes_ctr_decrypt(encrypted_msg_bytes, shared_key, iv_bytes)

        # In the UI, the result has an extra base64 encoding step also for the
        # symmetrical part of the encryption. If it fails, ignore it as it is
        # apparently not needed.
        # TODO v5+ adapt as stated above in decrypting shared key
        try:
            json.loads(result.decode(STRING_ENCODING))
        except json.decoder.JSONDecodeError:
            try:
                result = base64s_to_bytes(result.decode(STRING_ENCODING))
            except UnicodeDecodeError:
                pass
        return result

    def _crypt_stream(self, stream, key, iv, chunk_size=DEFAULT_CHUNK_SIZE):
        """
        Encrypt or decrypt a stream using AES-CTR. Since this is a
        symmetric encryption, the same function can be used for both
        encryption and decryption.

        Parameters
        ----------
        stream : file-like
            The input stream to process (must support .read()).
        key : bytes
            The AES key.
        iv : bytes
            The initialization vector.
        chunk_size : int
            The size of chunks to read and process.

        Yields
        ------
        bytes
            Processed data chunks.
        """
        self.log.debug("Processing stream with AES-CTR encryption/decryption")
        cipher = self._create_aes_cipher(key, iv)
        cryptor = cipher.encryptor()

        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            processed_chunk = cryptor.update(chunk)
            if processed_chunk:
                yield processed_chunk

        final_chunk = cryptor.finalize()
        if final_chunk:
            yield final_chunk

    def encrypt_stream(
        self, stream, pubkey_base64s: str, chunk_size=DEFAULT_CHUNK_SIZE
    ):
        """
        Encrypt a stream using hybrid RSA/AES encryption.

        A 32-byte (256-bit) random key is generated for AES-256 encryption.

        Parameters
        ----------
        stream : file-like
            The input stream to encrypt (must support .read()).
        pubkey_base64s : str
            The public key to use for encryption (PEM format, base64 string).
        chunk_size : int
            The size of chunks to read and encrypt.

        Yields
        ------
        bytes
            Header followed by encrypted data chunks.
        """
        shared_key = os.urandom(SHARED_ENCRYPT_KEY_LENGTH)
        iv_bytes = os.urandom(IV_LENGTH)
        self.log.debug("Encrypting stream with hybrid RSA/AES encryption")
        try:
            pubkey = self._load_public_key(pubkey_base64s)
        except Exception as e:
            self.log.error(f"Failed to load public key: {e}")
            raise ValueError("Invalid public key provided for encryption.") from e
        encrypted_key_bytes = pubkey.encrypt(shared_key, padding.PKCS1v15())

        encrypted_key_b64 = self.bytes_to_str(encrypted_key_bytes)
        iv_b64 = self.bytes_to_str(iv_bytes)

        header_str = f"{encrypted_key_b64}{SEPARATOR}{iv_b64}{SEPARATOR}"
        header_bytes = header_str.encode(STRING_ENCODING)
        # Yield the header first, then encrypt the rest of the data
        # chunk by chunk as it is being streamed.
        yield header_bytes
        yield from self._crypt_stream(stream, shared_key, iv_bytes, chunk_size)

    def decrypt_stream(self, stream, chunk_size=DEFAULT_CHUNK_SIZE):
        """
        Decrypt a stream that was encrypted using hybrid RSA/AES encryption.

        Parameters
        ----------
        stream : file-like
            The input stream to decrypt (must support .read()).
        chunk_size : int
            The size of chunks to read and decrypt.

        Yields
        ------
        bytes
            Decrypted data chunks.
        """
        self.log.debug(
            f"Decrypting stream with hybrid RSA/AES decryption (stream={type(stream).__name__})"
        )
        encrypted_key_b64, iv_b64, _ = self._read_header_from_stream(stream)
        encrypted_key_bytes = self.str_to_bytes(encrypted_key_b64)
        iv_bytes = self.str_to_bytes(iv_b64)

        shared_key = self.private_key.decrypt(encrypted_key_bytes, padding.PKCS1v15())
        # After shared key and iv are decrypted,
        # decrypt the rest chunk by chunk as data is being streamed.
        yield from self._crypt_stream(stream, shared_key, iv_bytes, chunk_size)

    def verify_public_key(self, pubkey_base64: str) -> bool:
        """
        Verifies the public key.

        Compare a public key with the generated public key from the private key
        that is stored in this instance. This is usefull for verifying that the
        public key stored on the server is derived from the currently used
        private key.

        Parameters
        ----------
        pubkey_base64: str
            The public key to verify as returned from the server.

        Returns
        -------
        bool
            True if the public key is valid, False otherwise.
        """
        public_key_server = base64s_to_bytes(pubkey_base64)
        return self.public_key_bytes == public_key_server
