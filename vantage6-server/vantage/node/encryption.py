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

TODO handle disabled encryption
TODO handle no public key from other organization (should that happen here)
TODO rename def, not all methods should be public
"""
import logging
import pickle

from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key
)

import vantage.constants as cs
from vantage.util import (
    Singleton,
    logger_name,
    prepare_bytes_for_transport,
    unpack_bytes_from_transport
)


class Cryptor(metaclass=Singleton):
    """ Wrapper class for the cryptography package.

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

    def __init__(self, private_key_file=None):
        self.log = logging.getLogger(logger_name(__name__))
        self.private_key = self.__load_private_key(private_key_file)

    def verify_public_key(self, public_key_base64) -> bool:
        """ Verifies the public key.

            Compare the public key with the generated public key from
            the private key that is stored in this instance. This is
            usefull for verifying that the public key stored on the
            server is derived from the currently used private key.

            :param public_key_base64: public_key as returned from the
                server (still base64 encoded)
        """
        public_key_server = unpack_bytes_from_transport(
            public_key_base64
        )
        return self.public_key_bytes == public_key_server

    @property
    def public_key_bytes(self):
        """ Returns the public key bytes from the organization.
        """
        return self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    @property
    def public_key_str(self):
        """ Returns a JSON safe public key, used for the API interface.
        """
        return prepare_bytes_for_transport(self.public_key_bytes)

    def encrypt_bytes_to_base64(self, msg: bytes, 
        public_key_base64: str) -> str:
        """ Encrypt a `msg` using `public_key_base64`.

            :param msg: message to be encrypted
            :param public_key_base64: public key base64 decoded 
                (directly from API transport)
            
            TODO we should retreive all keys once... and store them in 
                the node
        """
        
        # unpack public key
        public_key_bytes = unpack_bytes_from_transport(
            public_key_base64
        )
        
        # encrypt message using public key
        encrypted_msg = self.encrypt_bytes(msg, public_key_bytes)
        
        # prepare message for transport
        safe_chars_encoded_msg = prepare_bytes_for_transport(
            encrypted_msg
        )
        
        return safe_chars_encoded_msg

    def encrypt_bytes(self, msg: bytes, public_key_bytes: bytes) -> bytes:
        """ Encrypt `msg` using a `public_key_bytes`.
        
            :param msg: string message to encrypt
            :param public_key_bytes: public key used to encrypt `msg`
        """
        try:
            pub_key = load_pem_public_key(
                public_key_bytes,
                backend=default_backend()
            )
        except Exception as e:
            self.log.error("Unable to load public-key")
            self.log.debug(e)

        try:    
            encrypted_msg = pub_key.encrypt(
                msg,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
        except Exception as e:
            self.log.error("Unable to encrypt message")
            self.log.debug(e)

        return encrypted_msg
    
    def decrypt_bytes(self, msg: bytes) -> bytes:
        """ Decrypt `msg` using our private key.
        
            :param msg: bytes message
        """
        decrypted_msg = self.private_key.decrypt(
            msg,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        # return unencrypted and default unencoded msg
        return decrypted_msg

    def decrypt_bytes_from_base64(self, msg: str) -> bytes:
        """ Decrypt bytes `msg` using our private key

            :param msg: string utf-8 encoded base64 encrypted msg

            TODO else clausule does not make a lot of sense
        """
        
        if msg:
            msg_bytes = unpack_bytes_from_transport(msg)
            return self.decrypt_bytes(msg_bytes)
        else:
            return b""
    
    def __load_private_key(self, private_key_file=None):
        """ Load a private key file into this instance.
        
            If `private_key_file` has not been supplied the default key
            is used (which is fine in most cases). In case the file
            does not exist it is generated, make sure python has access
            to the filepath in case you have specified one.

            :param private_key_file: path to a private key file (or 
                where you want to store one)

            TODO consider making this a static function
        """

        # we use the default data folder, which is a folder in the 
        # package directory
        if not private_key_file:
            rsa_file = Path("/mnt/data/private_key.pem")
            self.log.debug(
                f"No private key file specified, " 
                f"using default (located in the data folder)"
            )
        else:
            rsa_file = private_key_file
        
        # this gets messy when python does not have access to the 
        # `rsa_file`
        if not rsa_file.exists():
            self.log.warning(
                f"Private key file {rsa_file} not found. Now generating one. "
                f"This is could be normal if you run {cs.APPNAME} for the first "
                f"time."
            )
            self.__create_new_rsa_key(rsa_file)
        
        self.log.debug("Loading private key")
        return load_pem_private_key(
            rsa_file.read_bytes(), 
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


class NoCryptor(Cryptor):
    """ When the collaboration of which the node part is is unencrypted.

        This overwrites all encryption / descryption methods to not 
        use encryption, but does cenvert between str and bytes if needed
    """
    def __init__(self, private_key_file=None):
        # super().__init__(private_key_file=private_key_file)
        self.log = logging.getLogger(logger_name(__name__))
        self.log.warning(
                "Encrpytion disabled! Use this only for debugging")

    
    def encrypt_bytes_to_base64(
        self, msg: bytes, public_key_base64: str) -> str:
        return prepare_bytes_for_transport(msg)

    def encrypt_bytes(self, msg: bytes, public_key_bytes: bytes) -> bytes:
        return msg
    
    def decrypt_bytes(self, msg: bytes) -> bytes:
        return msg

    def decrypt_bytes_from_base64(self, msg: str) -> bytes:
        return unpack_bytes_from_transport(msg)
