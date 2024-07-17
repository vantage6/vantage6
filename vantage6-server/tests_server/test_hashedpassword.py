import unittest

from vantage6.server.hashedpassword import HashedPassword


class TestHashedPassword(unittest.TestCase):
    def test_valid_hash(self):
        # hash 'vantage6test'
        HashedPassword("$2b$12$qywY/MVIAVm6YUPfAWZR5OBUCWFEF58FwdKas7Mhcb.HkICkXAzUe")

    def test_invalid_hash_length(self):
        # missing last character
        with self.assertRaises(ValueError):
            HashedPassword(
                "$2b$12$qywY/MVIAVm6YUPfAWZR5OBUCWFEF58FwdKas7Mhcb.HkICkXAzU"
            )

    def test_invalid_hash(self):
        # didn't understand the assignment
        with self.assertRaises(ValueError):
            HashedPassword("superpassword")

    def test_empty_hash(self):
        # empty bcrypt hash
        with self.assertRaises(ValueError):
            HashedPassword("")

    def test_empty_string_hash(self):
        # hash of empty string
        with self.assertRaises(ValueError):
            HashedPassword(
                "$2b$12$iMwnJmCzBO0Jki.Lu4Qfmuv80L7FGbLLAPRYIxzWUhjnjbG/xxCjm"
            )

    def test_not_bcrypt_hash(self):
        # not a bcrypt hash
        with self.assertRaises(ValueError):
            HashedPassword(
                "$6$yWchObbpqtS2nXY6$DRBLkAeuUqkHlRurtHtqQ1OK73/jdxhsSomHK1pnXuiKFvJ.mKDQIMU99hS/kHmi3rgeLAd7X0PlWCkRjnFDj/"
            )

    def test_older_version(self):
        # 2a version hashing 'vantage6test'
        with self.assertRaises(ValueError):
            HashedPassword(
                "$2a$12$4SBnOHg0PqtzLQu/vN0.4un3N21G3tJazxBuu9hJSi0WbF9LRONdm"
            )
