from unittest import TestCase

from vantage6.mock.util import env_vars


class TestEnvVars(TestCase):
    def test_env_vars_context_manager(self):
        """Test if env_vars context manager sets and restores environment variables"""
        test_vars = {"TEST_VAR1": "value1", "TEST_VAR2": "value2"}

        # Test setting new environment variables
        with env_vars(**test_vars):
            import os

            self.assertEqual(os.environ["TEST_VAR1"], "value1")
            self.assertEqual(os.environ["TEST_VAR2"], "value2")

        # Test variables are removed after context
        import os

        self.assertNotIn("TEST_VAR1", os.environ)
        self.assertNotIn("TEST_VAR2", os.environ)

    def test_env_vars_existing_variables(self):
        """Test if env_vars properly handles existing environment variables"""
        import os

        # Set an existing variable
        os.environ["EXISTING_VAR"] = "original"

        test_vars = {"EXISTING_VAR": "temporary"}

        # Test overwriting existing variable
        with env_vars(**test_vars):
            self.assertEqual(os.environ["EXISTING_VAR"], "temporary")

        # Test original value is restored
        self.assertEqual(os.environ["EXISTING_VAR"], "original")

        # Clean up
        del os.environ["EXISTING_VAR"]

    def test_env_vars_nested(self):
        """Test if env_vars works with nested context managers"""
        test_vars_1 = {"TEST_VAR": "value1"}
        test_vars_2 = {"TEST_VAR": "value2"}

        with env_vars(**test_vars_1):
            import os

            self.assertEqual(os.environ["TEST_VAR"], "value1")

            with env_vars(**test_vars_2):
                self.assertEqual(os.environ["TEST_VAR"], "value2")

            self.assertEqual(os.environ["TEST_VAR"], "value1")

        self.assertNotIn("TEST_VAR", os.environ)
