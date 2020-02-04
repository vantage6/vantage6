import logging
import unittest
import yaml
import bcrypt
import datetime
import json

# from sqlalchemy import create_engine
# from sqlalchemy.orm import Session
from cryptography.hazmat.primitives import hashes, serialization

from vantage.node.encryption import Cryptor
# from vantage.server.controller.fixture import load
# from vantage.server.model.base import Database, Base
from vantage.constants import PACAKAGE_FOLDER, APPNAME, DATA_FOLDER
from vantage.util import unpack_bytes_from_transport

# from vantage.server.model import (
#     Base,
#     User,
#     Organization,
#     Collaboration,
#     Task,
#     Result,
#     Node
# )

log = logging.getLogger(__name__.split(".")[-1])
log.level = logging.DEBUG

class TestCryptor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.private_key_file = DATA_FOLDER / "unit_test_privkey.pem"
        cls.cryptor = Cryptor(cls.private_key_file)
    
    @classmethod
    def tearDownClass(cls):
        cls.private_key_file.unlink()

    def test_load_rsa_from_file(self):
        private_key = self.cryptor._Cryptor__load_private_key(
            self.private_key_file
        )
    
        public_key = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.assertIsInstance(public_key, bytes)

    def test_public_bytes(self):
        self.assertIsInstance(
            self.cryptor.public_key_bytes, 
            bytes
        )

    def test_transport_key(self):
        self.assertIsInstance(
            self.cryptor.public_key_str,
            str
        )

    def test_unpacking_transport_key(self):
        b = unpack_bytes_from_transport(
            self.cryptor.public_key_str
        )
        self.assertEqual(
            b, 
            self.cryptor.public_key_bytes
        )

    def test_encryption_decryption(self):
        msg = json.dumps({"msg":"some message!"}).encode("ascii")
        encrypted = self.cryptor.encrypt_bytes_to_base64(
            msg,
            self.cryptor.public_key_str
        )
        self.assertNotEqual(msg, encrypted)
        
        unencrypted = self.cryptor.decrypt_bytes_from_base64(
            encrypted
        )
        self.assertEqual(msg, unencrypted)

    def test_creating_a_new_key(self):
        tmp = DATA_FOLDER / "unit_test_key.pem"
        self.cryptor._Cryptor__create_new_rsa_key(
            tmp
        )
        self.assertTrue(tmp.exists())
        tmp.unlink()

    