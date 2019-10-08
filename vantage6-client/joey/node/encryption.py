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
import base64

from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key, 
    load_pem_public_key 
)

import joey.constants as cs
from joey.util import (
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
        needs to be executed (and also a ascii encoding needs to be applied
        because of the way python implemented base64). The same goed for
        sending and receiving the public_key.
    """

    def __init__(self, private_key_file=None, disabled=False):
        self.log = logging.getLogger(logger_name(__name__))
        if disabled:
            self.log.warning(
                "Encrpytion disabled! Use this only for debugging")
        self.disabled = disabled

        # we dont need to load it...
        if not self.disabled:
            self.private_key = self.__load_private_key(private_key_file)

    def verify_public_key(self, public_key_base64):
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
        local_bytes = self.public_key_bytes
        return self.public_key_bytes == public_key_server

    @property
    def public_key_bytes(self):
        """ Returns the public key bytes from the organization.
        """
        # TODO what needs to be returned if encryption is disabled
        if not self.disabled:
            return self.private_key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        return ""

    @property
    def public_key_str(self):
        """ Returns a JSON safe public key, used for the API interface.
        """
        return prepare_bytes_for_transport(self.public_key_bytes)
        
    def encrypt_base64(self, msg: str, public_key_base64: str) -> str:
        """ Encrypt a `msg` using `public_key_base64`.

            :param msg: message to be encrypted
            :param public_key_base64: public key base64 decoded 
                (directly from API transport)
            
            TODO we should retreive all keys once... and store them in 
                the node
        """
        # decode the b64, ascii key to bytes
        public_key_bytes = unpack_bytes_from_transport(
            public_key_base64
        )
        
        encrypted_msg = self.encrypt(msg, public_key_bytes)

        safe_chars_encoded_msg = prepare_bytes_for_transport(
            encrypted_msg
        )
        # encode message using this key
        return safe_chars_encoded_msg

    def encrypt(self, msg: str, public_key_bytes: bytes) -> bytes:
        """ Encrypt `msg` using a `public_key_bytes`.
        
            :param msg: string message to encrypt
            :param public_key_bytes: public key used to encrypt `msg`
        """
        if self.disabled:
            return msg
        
        pub_key = load_pem_public_key(
            public_key_bytes,
            backend=default_backend()
        )

        encrypted_msg = pub_key.encrypt(
            msg.encode("ascii"),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return encrypted_msg
    
    def decrypt_base64(self, msg: bytes) -> bytes:
        """ Decrypt bytes `msg` using our private key

            :param msg: string ascii encoded base64 encrypted msg
        """
        
        if msg:
            msg_bytes = unpack_bytes_from_transport(msg)
            return self.decrypt_bytes(msg_bytes)
        else:
            return b""

    def decrypt_base64_to_str(self, msg: bytes) -> str:
        """ Decrypt bytes `msg` using our private key

            :param msg: string ascii encoded base64 encrypted msg
        """
        return self.decrypt_base64(msg).decode("ascii")
    
    def decrypt_bytes(self, msg: bytes) -> bytes:
        """ Decrypt `msg` using our private key.
        
            :param msg: bytes message
        """
        
        if self.disabled:
            return msg
        
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
            rsa_file = cs.DATA_FOLDER / "private_key.pem"
            self.log.debug(
                f"No private key file specified, " 
                f"using default: {rsa_file}"
            )
        else:
            rsa_file = Path(private_key_file)
        
        # this gets messy when python does not have access to the 
        # `rsa_file`
        if not rsa_file.exists():
            self.log.warning(
                f"No default private key found. Now generating one. "
                f"This is normal if you run {cs.APPNAME} for the first "
                f"time."
            )
            self.__create_new_rsa_key(rsa_file)
        
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
