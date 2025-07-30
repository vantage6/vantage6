#!/usr/bin/env python3
"""
Test script to demonstrate the EnumBase functionality
"""

from vantage6.common.enum import EnumBase

from vantage6.algorithm.store.globals import ConditionalArgComparator


class TestEnum(EnumBase):
    """Test enum to demonstrate functionality"""

    VALUE_1 = "test1"
    VALUE_2 = "test2"
    VALUE_3 = "test3"


def test_enum_base_functionality():
    """Test the EnumBase list() method"""
    print("Testing EnumBase functionality:")
    print(f"TestEnum.list(): {TestEnum.list()}")
    print(f"TestEnum.names(): {TestEnum.names()}")
    print(f"TestEnum.items(): {TestEnum.items()}")
    print()

    print("Testing ConditionalArgComparator:")
    print(f"ConditionalArgComparator.list(): {ConditionalArgComparator.list()}")
    print(f"ConditionalArgComparator.names(): {ConditionalArgComparator.names()}")
    print(f"ConditionalArgComparator.items(): {ConditionalArgComparator.items()}")


if __name__ == "__main__":
    test_enum_base_functionality()
