from unittest import TestCase
from unittest.mock import MagicMock, patch

import click
from click.testing import CliRunner
from vantage6.server.cli.server import cli_server_shell, click_insert_context


@click.command(name="dummy")
@click_insert_context
def _dummy_command(ctx):
    """Minimal command to exercise click_insert_context in isolation."""
    click.echo("ran-with-ctx")


class TestClickInsertContext(TestCase):
    """click_insert_context must hard-error, not prompt, when no name/config is given."""

    def test_no_name_or_config_errors_without_prompting(self):
        runner = CliRunner()
        result = runner.invoke(_dummy_command, [])
        self.assertEqual(result.exit_code, 1)

    def test_nonexistent_name_errors_without_prompting(self):
        runner = CliRunner()
        with patch(
            "vantage6.server.cli.server.ServerContext.config_exists",
            return_value=False,
        ):
            result = runner.invoke(_dummy_command, ["--name", "does-not-exist"])
        self.assertEqual(result.exit_code, 1)

    def test_existing_name_connects_the_database_and_runs_the_command(self):
        runner = CliRunner()
        mock_ctx = MagicMock()
        mock_ctx.config = {"allow_drop_all": False}
        with (
            patch(
                "vantage6.server.cli.server.ServerContext.config_exists",
                return_value=True,
            ),
            patch("vantage6.server.cli.server.ServerContext", return_value=mock_ctx),
            patch("vantage6.server.cli.server.Database") as mock_database_class,
        ):
            result = runner.invoke(_dummy_command, ["--name", "my-server"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("ran-with-ctx", result.output)
        mock_database_class.return_value.connect.assert_called_once_with(
            uri=mock_ctx.get_database_uri.return_value, allow_drop_all=False
        )

    def test_explicit_config_path_bypasses_name_lookup_entirely(self):
        mock_ctx = MagicMock()
        mock_ctx.config = {"allow_drop_all": False}
        runner = CliRunner()
        with (
            patch(
                "vantage6.server.cli.server.ServerContext.from_external_config_file",
                return_value=mock_ctx,
            ) as mock_from_file,
            patch(
                "vantage6.server.cli.server.ServerContext.config_exists"
            ) as mock_config_exists,
            patch("vantage6.server.cli.server.Database"),
        ):
            result = runner.invoke(_dummy_command, ["--config", "/mnt/config.yaml"])
        self.assertEqual(result.exit_code, 0, result.output)
        mock_from_file.assert_called_once()
        mock_config_exists.assert_not_called()


class TestCliServerShell(TestCase):
    """cli_server_shell must give a clear error, not a traceback, when IPython is missing."""

    def test_missing_ipython_gives_a_clear_error_instead_of_a_traceback(self):
        mock_ctx = MagicMock()
        mock_ctx.config = {"allow_drop_all": False}
        runner = CliRunner()
        with (
            patch(
                "vantage6.server.cli.server.ServerContext.config_exists",
                return_value=True,
            ),
            patch("vantage6.server.cli.server.ServerContext", return_value=mock_ctx),
            patch("vantage6.server.cli.server.Database"),
            patch.dict("sys.modules", {"IPython": None, "traitlets.config": None}),
        ):
            result = runner.invoke(cli_server_shell, ["--name", "my-server"])
        self.assertEqual(result.exit_code, 1)
