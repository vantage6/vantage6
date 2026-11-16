"""
Test script to demonstrate the StrEnumBase functionality
"""

import unittest

from vantage6.common.enum import StrEnumBase
from vantage6.common.globals import APPNAME, InstanceType


class TestEnum(StrEnumBase):
    """Test enum to demonstrate functionality"""

    VALUE_1 = "test1"
    VALUE_2 = "test2"
    VALUE_3 = "test3"


class TestEnumBase(unittest.TestCase):
    def test_enum_base_functionality(self):
        """Test the StrEnumBase list() method"""

        assert TestEnum.list() == ["test1", "test2", "test3"]
        assert TestEnum.names() == ["value_1", "value_2", "value_3"]
        assert TestEnum.items() == [
            ("value_1", "test1"),
            ("value_2", "test2"),
            ("value_3", "test3"),
        ]

    def test_str(self):
        """Test that str() of a member is its value on every Python version"""
        self.assertEqual(str(TestEnum.VALUE_1), "test1")

    def test_format(self):
        """
        Test that format() and f-strings render the value

        Python 3.11 changed this for enums with a mixed-in str type, see
        https://github.com/vantage6/vantage6/issues/2512
        """
        self.assertEqual(f"{TestEnum.VALUE_1}", "test1")
        self.assertEqual("{}".format(TestEnum.VALUE_2), "test2")
        self.assertEqual(format(TestEnum.VALUE_3, ">6"), " test3")

    def test_identifiers_from_issue_2512(self):
        """Test the container label and log file name shapes from the issue"""
        self.assertEqual(f"{APPNAME}-type={InstanceType.NODE}", f"{APPNAME}-type=node")
        self.assertEqual(f"{InstanceType.NODE}_user.log", "node_user.log")
