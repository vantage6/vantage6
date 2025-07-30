#!/usr/bin/env python3
"""
Test script to demonstrate the EnumBase functionality
"""

from vantage6.common.enum import EnumBase


class TestEnum(EnumBase):
    """Test enum to demonstrate functionality"""

    VALUE_1 = "test1"
    VALUE_2 = "test2"
    VALUE_3 = "test3"


def test_enum_base_functionality():
    """Test the EnumBase list() method"""

    assert TestEnum.list() == ["test1", "test2", "test3"]
    assert TestEnum.names() == ["value_1", "value_2", "value_3"]
    assert TestEnum.items() == [
        ("value_1", "test1"),
        ("value_2", "test2"),
        ("value_3", "test3"),
    ]


if __name__ == "__main__":
    test_enum_base_functionality()
