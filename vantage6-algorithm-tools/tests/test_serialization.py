from pytest import mark

from vantage6.common import serialization
import pandas as pd


@mark.parametrize(
    "data,target",
    [
        # Default serialization
        ([1, 2, 3], "[1, 2, 3]"),
        ("hello", '"hello"'),
        ({"hello": "goodbye"}, '{"hello": "goodbye"}'),
        # Pandas serialization
        (
            pd.DataFrame([[1, 2, 3]], columns=["one", "two", "three"]),
            '{"one":{"0":1},"two":{"0":2},"three":{"0":3}}',
        ),
        (pd.Series([1, 2, 3]), '{"0":1,"1":2,"2":3}'),
    ],
)
def test_json_serialization(data, target):
    result = serialization.serialize(data)

    assert target == result.decode()
