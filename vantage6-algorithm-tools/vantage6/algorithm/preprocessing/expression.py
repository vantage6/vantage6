"""
Safe evaluation of expressions on pandas DataFrames.

Expressions are provided by users as task arguments, so they must not be evaluated with
``pandas.DataFrame.eval`` or ``pandas.DataFrame.query``: those allow attribute access and
method calls, and can be used to execute arbitrary code. Instead, the expression is
parsed with :mod:`ast` and evaluated by walking the syntax tree, supporting only:

- column names, e.g. ``age`` (columns must be valid Python identifiers)
- numbers, strings, ``True``, ``False`` and ``None``
- arithmetic: ``+``, ``-``, ``*``, ``/``, ``//``, ``%`` (only ``+`` for text)
- comparisons: ``==``, ``!=``, ``<``, ``<=``, ``>``, ``>=``, also chained (``1 < a < 5``)
- membership in a list of constants: ``a in [1, 2]``, ``a not in ['x', 'y']``
- logical operators: ``and``, ``or``, ``not``, ``&``, ``|``, ``~``
- the functions ``abs``, ``sqrt``, ``log``, ``log2``, ``log10``, ``exp``, ``floor``,
  ``ceil`` and ``round`` (``round(a)`` or ``round(a, 2)``)

Anything else, such as other functions, attribute access (``a.b``), indexing
(``a[0]``) and exponentiation (``**``), is rejected. Expressions may be at most
``MAX_EXPRESSION_LENGTH`` characters long.
"""

import ast
import operator
from collections.abc import Callable
from typing import Any

import numpy as np
import pandas as pd

from vantage6.algorithm.tools.exceptions import UserInputError

MAX_EXPRESSION_LENGTH = 250

_BINARY_OPERATORS: dict[type[ast.operator], Callable] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.BitAnd: operator.and_,
    ast.BitOr: operator.or_,
}

_COMPARISON_OPERATORS: dict[type[ast.cmpop], Callable] = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}

# Functions that may be called in expressions, with the number of arguments they take
_FUNCTIONS: dict[str, tuple[Callable, int]] = {
    "abs": (np.abs, 1),
    "sqrt": (np.sqrt, 1),
    "log": (np.log, 1),
    "log2": (np.log2, 1),
    "log10": (np.log10, 1),
    "exp": (np.exp, 1),
    "floor": (np.floor, 1),
    "ceil": (np.ceil, 1),
}
# `round` is handled separately, as its second argument must be an integer constant
_SUPPORTED_FUNCTIONS = sorted([*_FUNCTIONS, "round"])

_CONSTANT_TYPES = (int, float, str, bool, type(None))


def evaluate_expression(df: pd.DataFrame, expression: str) -> Any:
    """
    Evaluate an expression on a DataFrame.

    See the module docstring for the supported syntax.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame whose columns may be used in the expression.
    expression : str
        The expression to evaluate.

    Returns
    -------
    Any
        The result of the expression: usually a pandas Series, or a scalar if the
        expression does not refer to any column.

    Raises
    ------
    UserInputError
        If the expression is too long, cannot be parsed or uses unsupported syntax.
    """
    if not isinstance(expression, str):
        raise UserInputError("Expression must be a string.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise UserInputError(
            f"Expression is too long (maximum is {MAX_EXPRESSION_LENGTH} characters)."
        )
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except (SyntaxError, ValueError, RecursionError, MemoryError):
        raise UserInputError("Expression could not be parsed.") from None
    return _Evaluator(df).visit(tree.body)


class _Evaluator:
    """Evaluate the nodes of a parsed expression that are explicitly supported."""

    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df

    def visit(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Name):
            return self._visit_name(node)
        if isinstance(node, ast.Constant):
            return self._visit_constant(node)
        if isinstance(node, ast.BinOp):
            return self._visit_binop(node)
        if isinstance(node, ast.UnaryOp):
            return self._visit_unaryop(node)
        if isinstance(node, ast.BoolOp):
            return self._visit_boolop(node)
        if isinstance(node, ast.Compare):
            return self._visit_compare(node)
        if isinstance(node, ast.Call):
            return self._visit_call(node)
        raise UserInputError(_unsupported(node))

    def _visit_name(self, node: ast.Name) -> pd.Series:
        if node.id not in self.df.columns:
            raise UserInputError(f"Column '{node.id}' does not exist.")
        return self.df[node.id]

    @staticmethod
    def _visit_constant(node: ast.Constant) -> Any:
        if not isinstance(node.value, _CONSTANT_TYPES):
            raise UserInputError(_unsupported(node))
        return node.value

    def _visit_binop(self, node: ast.BinOp) -> Any:
        op = _BINARY_OPERATORS.get(type(node.op))
        if op is None:
            raise UserInputError(_unsupported(node.op))
        left, right = self.visit(node.left), self.visit(node.right)
        # only allow joining text, as e.g. repeating text (`'x' * 999999999`) could
        # use excessive memory
        if not isinstance(node.op, ast.Add) and (_is_text(left) or _is_text(right)):
            raise UserInputError("Only '+' is supported for text.")
        return op(left, right)

    def _visit_unaryop(self, node: ast.UnaryOp) -> Any:
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        if isinstance(node.op, (ast.Not, ast.Invert)):
            # like pandas, `not` and `~` are element-wise negations of booleans
            if isinstance(operand, (bool, np.bool_)):
                return not operand
            return ~operand
        raise UserInputError(_unsupported(node.op))

    def _visit_boolop(self, node: ast.BoolOp) -> Any:
        # like pandas, `and` and `or` are evaluated element-wise
        op = operator.and_ if isinstance(node.op, ast.And) else operator.or_
        result = self.visit(node.values[0])
        for value in node.values[1:]:
            result = op(result, self.visit(value))
        return result

    def _visit_compare(self, node: ast.Compare) -> Any:
        result = None
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, (ast.In, ast.NotIn)):
                right = self._visit_constant_list(comparator)
                comparison = _isin(left, right)
                if isinstance(op, ast.NotIn):
                    comparison = (
                        not comparison if isinstance(comparison, bool) else ~comparison
                    )
            else:
                compare = _COMPARISON_OPERATORS.get(type(op))
                if compare is None:
                    raise UserInputError(_unsupported(op))
                right = self.visit(comparator)
                comparison = compare(left, right)
            # chained comparisons (e.g. `1 < a < 5`) must all be true
            result = comparison if result is None else operator.and_(result, comparison)
            left = right
        return result

    def _visit_constant_list(self, node: ast.AST) -> list:
        if not isinstance(node, (ast.List, ast.Tuple)) or not all(
            isinstance(element, ast.Constant) for element in node.elts
        ):
            raise UserInputError(
                "Only a list of constants is supported after 'in' or 'not in'."
            )
        return [self._visit_constant(element) for element in node.elts]

    def _visit_call(self, node: ast.Call) -> Any:
        if (
            not isinstance(node.func, ast.Name)
            or node.func.id not in _SUPPORTED_FUNCTIONS
        ):
            raise UserInputError(
                f"Only the functions {', '.join(_SUPPORTED_FUNCTIONS)} are supported."
            )
        name = node.func.id
        if node.keywords:
            raise UserInputError(
                f"Function '{name}' does not accept keyword arguments."
            )
        if name == "round":
            return self._visit_round(node)
        function, n_args = _FUNCTIONS[name]
        if len(node.args) != n_args:
            raise UserInputError(f"Function '{name}' takes {n_args} argument(s).")
        return function(*(self.visit(arg) for arg in node.args))

    def _visit_round(self, node: ast.Call) -> Any:
        if len(node.args) not in (1, 2):
            raise UserInputError("Function 'round' takes 1 or 2 arguments.")
        decimals = 0
        if len(node.args) == 2:
            arg = node.args[1]
            if not (
                isinstance(arg, ast.Constant)
                and isinstance(arg.value, int)
                and not isinstance(arg.value, bool)
            ):
                raise UserInputError(
                    "The number of decimals of 'round' must be an integer."
                )
            decimals = arg.value
        return np.round(self.visit(node.args[0]), decimals)


def _is_text(value: Any) -> bool:
    if isinstance(value, pd.Series):
        return pd.api.types.is_string_dtype(value) or pd.api.types.is_object_dtype(
            value
        )
    return isinstance(value, str)


def _isin(value: Any, options: list) -> Any:
    if isinstance(value, pd.Series):
        return value.isin(options)
    return value in options


def _unsupported(node: ast.AST) -> str:
    return f"'{type(node).__name__}' is not supported in expressions."
