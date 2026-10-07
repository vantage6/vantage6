import traceback
import unittest

from vantage6.algorithm.tools.error_handling import handle_data_errors
from vantage6.algorithm.tools.exceptions import AlgorithmRuntimeError, UserInputError


class TestHandleDataErrors(unittest.TestCase):
    def test_non_pandas_error_is_sanitized(self):
        """Errors that are not raised by vantage6 should not leak any details."""

        @handle_data_errors
        def func():
            raise ValueError("could not convert string to float: 'secret_42'")

        with self.assertRaises(AlgorithmRuntimeError) as ctx:
            func()

        self.assertNotIn("secret_42", str(ctx.exception))
        # the original error should not be printed when the traceback is logged
        traceback_ = "".join(traceback.format_exception(ctx.exception))
        self.assertNotIn("secret_42", traceback_)

    def test_algorithm_errors_pass_through(self):
        """Vantage6 errors are meant for the user and should not be replaced."""

        @handle_data_errors
        def func():
            raise UserInputError("old_names and new_names must have the same length")

        with self.assertRaises(UserInputError):
            func()


if __name__ == "__main__":
    unittest.main()
