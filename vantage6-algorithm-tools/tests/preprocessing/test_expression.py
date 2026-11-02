import inspect
import unittest

import numpy as np
import pandas as pd

from vantage6.algorithm.tools.exceptions import UserInputError

from vantage6.algorithm.preprocessing.column import assign_column, redefine_column
from vantage6.algorithm.preprocessing.expression import (
    MAX_EXPRESSION_LENGTH,
    evaluate_expression,
)
from vantage6.algorithm.preprocessing.filtering import select_rows

# The decorators require a running algorithm container, so test the wrapped functions
_assign_column = inspect.unwrap(assign_column)
_redefine_column = inspect.unwrap(redefine_column)
_select_rows = inspect.unwrap(select_rows)


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "a": [1, 2, 3, 4, 5],
            "b": [6, 7, 8, 9, 10],
            "c": [11, 12, 13, 14, 15],
            "s": ["x", "y", "x", "z", "y"],
        }
    )


class TestEvaluateExpression(unittest.TestCase):
    def assert_series_equal(self, expression: str, expected: pd.Series) -> None:
        pd.testing.assert_series_equal(
            evaluate_expression(_df(), expression), expected, check_names=False
        )

    def test_arithmetic(self):
        df = _df()
        self.assert_series_equal("a + b * 2", df.a + df.b * 2)
        self.assert_series_equal("(a - b) / c", (df.a - df.b) / df.c)
        self.assert_series_equal("c // a % 3", df.c // df.a % 3)
        self.assert_series_equal("-a", -df.a)
        self.assert_series_equal("+a", df.a)

    def test_comparisons(self):
        df = _df()
        self.assert_series_equal("a > 2", df.a > 2)
        self.assert_series_equal("a == 3", df.a == 3)
        self.assert_series_equal("a != 3", df.a != 3)
        self.assert_series_equal("s == 'x'", df.s == "x")
        self.assert_series_equal("2 <= a < 5", (df.a >= 2) & (df.a < 5))

    def test_membership(self):
        df = _df()
        self.assert_series_equal("a in [1, 5]", df.a.isin([1, 5]))
        self.assert_series_equal("s not in ('x', 'y')", ~df.s.isin(["x", "y"]))

    def test_logical_operators(self):
        df = _df()
        self.assert_series_equal("a > 2 and b < 10", (df.a > 2) & (df.b < 10))
        self.assert_series_equal("a > 4 or c < 12", (df.a > 4) | (df.c < 12))
        self.assert_series_equal("not a > 2", ~(df.a > 2))
        self.assert_series_equal("(a > 2) & (b < 10)", (df.a > 2) & (df.b < 10))
        self.assert_series_equal("(a > 4) | (c < 12)", (df.a > 4) | (df.c < 12))
        self.assert_series_equal("~(a > 2)", ~(df.a > 2))

    def test_functions(self):
        df = _df()
        for name, function in [
            ("abs", np.abs),
            ("sqrt", np.sqrt),
            ("log", np.log),
            ("log2", np.log2),
            ("log10", np.log10),
            ("exp", np.exp),
            ("floor", np.floor),
            ("ceil", np.ceil),
        ]:
            with self.subTest(function=name):
                self.assert_series_equal(f"{name}(a / 3)", function(df.a / 3))
        self.assert_series_equal("round(a / 3)", np.round(df.a / 3))
        self.assert_series_equal("round(a / 3, 2)", np.round(df.a / 3, 2))
        self.assert_series_equal("sqrt(log(b) + 1)", np.sqrt(np.log(df.b) + 1))

    def test_text(self):
        df = _df()
        self.assert_series_equal("s + '_1'", df.s + "_1")
        for expression in [
            "s * 999999999",
            "'x' * 999999999",
            "999999999 * s",
            "s - 'x'",
        ]:
            with (
                self.subTest(expression=expression),
                self.assertRaises(UserInputError),
            ):
                evaluate_expression(df, expression)

    def test_constants(self):
        self.assertEqual(evaluate_expression(_df(), "1 + 2"), 3)
        self.assertEqual(evaluate_expression(_df(), "not True"), False)
        self.assertEqual(evaluate_expression(_df(), "  1  "), 1)

    def test_rejects_code_execution(self):
        rejected = [
            # attribute chain to reach the os module
            "a.__class__.__init__.__globals__.get('sys').modules.get('os').getpid()",
            "a.sum()",
            "a.values",
            "log(a).real",
            "__import__('os')",
            "eval('1')",
            "exec('1')",
            "open('/etc/passwd')",
            "getattr(a, 'sum')()",
            "(lambda: 1)()",
            "log(a)(1)",
        ]
        for expression in rejected:
            with (
                self.subTest(expression=expression),
                self.assertRaises(UserInputError),
            ):
                evaluate_expression(_df(), expression)

    def test_rejects_unsupported_syntax(self):
        rejected = [
            "a ** 2",
            "a @ b",
            "a << 1",
            "a[0]",
            "a is None",
            "[1, 2]",
            "{'x': 1}",
            "f'{a}'",
            "a if b else c",
            "b'bytes'",
            "1j",
            "...",
            "a in b",
            "a in [b]",
            "x := 1",
            "@a",
            "`a`",
            "log(a, 2)",
            "log()",
            "log(a=1)",
            "round(a, 1.5)",
            "round(a, True)",
            "round(a, b)",
            "round(a, 1, 2)",
            "unknown_column + 1",
            "",
            "a +",
        ]
        for expression in rejected:
            with (
                self.subTest(expression=expression),
                self.assertRaises(UserInputError),
            ):
                evaluate_expression(_df(), expression)

    def test_rejects_non_string(self):
        with self.assertRaises(UserInputError):
            evaluate_expression(_df(), 1)

    def test_maximum_length(self):
        expression = "a" + " + a" * ((MAX_EXPRESSION_LENGTH - 1) // 4)
        self.assertLessEqual(len(expression), MAX_EXPRESSION_LENGTH)
        evaluate_expression(_df(), expression)
        with self.assertRaises(UserInputError):
            evaluate_expression(_df(), expression + " + a")


class TestPreprocessingFunctions(unittest.TestCase):
    def test_assign_column(self):
        df = _assign_column(_df(), "d", "a + b")
        self.assertEqual(df["d"].tolist(), [7, 9, 11, 13, 15])

    def test_assign_column_rejects_code(self):
        with self.assertRaises(UserInputError):
            _assign_column(_df(), "d", "a.sum()")

    def test_redefine_column(self):
        df = _redefine_column(_df(), "c", "a * b")
        self.assertEqual(df["c"].tolist(), [6, 14, 24, 36, 50])

    def test_redefine_column_rejects_code(self):
        with self.assertRaises(UserInputError):
            _redefine_column(_df(), "c", "a.sum()")

    def test_select_rows(self):
        df = _select_rows(_df(), "a > 2 and s != 'z'")
        self.assertEqual(df["a"].tolist(), [3, 5])
        self.assertEqual(df.index.tolist(), [2, 4])

    def test_select_rows_rejects_code(self):
        with self.assertRaises(UserInputError):
            _select_rows(_df(), "a.sum() > 0")

    def test_select_rows_requires_boolean(self):
        for query in ["a + 1", "True", "s"]:
            with self.subTest(query=query), self.assertRaises(UserInputError):
                _select_rows(_df(), query)
