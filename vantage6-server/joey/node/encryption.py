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
from joey.util import Singleton

class Cryptor(metaclass=Singleton):

    def __init__(self, private_key_file=None, disabled=False):
        self.log = logging.getLogger(__name__)
        if disabled:
            self.log.warning(
                "Encrpytion disabled! Use this only for debugging")
        self.disabled = disabled
        self.private_key = self.__load_private_key(private_key_file)

        # verify key with the key at the server. Also make sure that
        # a key is stored at the server

    def verify_public_key(self, server_public_key_bytes):
        
        local_bytes = self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return local_bytes == server_public_key_bytes

    def __load_private_key(self, private_key_file=None):
        if not private_key_file:
            rsa_file = cs.DATA_FOLDER / "private_key.pem"
            self.log.debug(
                f"No private key file specified, using default: {rsa_file}")
            
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
        """Creates a new RSA key for E2EE."""
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
        return self.private_key.public_key().public_bytes(
           encoding=serialization.Encoding.PEM,
           format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

    @property
    def public_key_str(self):
        return base64.b64encode(self.public_key_bytes).decode('ascii')

    def encrypt_using_base64(self, msg, public_key_base64):
        # TODO we should retreive all keys once... and store them in the node

        # decode the b64, ascii key to bytes
        public_key_bytes = base64.b64decode(public_key_base64)
        
        # encode message using this key
        return self.decrypt(self, msg, public_key_bytes)

    def encrypt(self, msg, public_key_bytes):
        """Encrypt a message for a specific organization."""
        if self.disabled:
            return msg
        
        pub_key = load_pem_public_key(
            public_key_bytes,
            backend=default_backend()
        )

        encrypted_msg = pub_key.encrypt(
            msg,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

        safe_chars_encoded_msg = base64.encodebytes(encrypted_msg)\
            .decode("ascii")

        return safe_chars_encoded_msg
    
    def decrypt_base64(self, msg):
        # msg is base64 ascii 
        msg_bytes = base64.b64decode(msg)
        return decrypt_bytes(msg_bytes)

    def decrypt_bytes(self, msg):
        """Decrpyt a message that is destined for us."""
        
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


