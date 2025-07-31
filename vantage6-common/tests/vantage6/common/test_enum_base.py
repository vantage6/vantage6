#!/usr/bin/env python3
"""
Test script to demonstrate the StrEnumBase functionality
"""

import unittest

from vantage6.common.enum import StrEnumBase


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
