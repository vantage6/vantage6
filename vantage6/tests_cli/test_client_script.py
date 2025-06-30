# from click import UsageError
# from vantage6.cli.test.client_script import cli_test_client_script

# import click
# import unittest


# class TestScriptTest(unittest.TestCase):
#     def test_script_incorrect_usage(self):
#         ctx = click.Context(cli_test_client_script)

#         with self.assertRaises(UsageError):
#             ctx.invoke(
#                 cli_test_client_script,
#                 script="path/to/script.py",
#                 task_arguments="{'my_arg': 1}",
#             )

#         with self.assertRaises(UsageError):
#             ctx.invoke(
#                 cli_test_client_script,
#                 task_arguments="not_a_json",
#             )
