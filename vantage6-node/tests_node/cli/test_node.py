from unittest import TestCase
from unittest.mock import patch

from click.testing import CliRunner
from vantage6.node.cli.node import cli_node_start


class TestCliNodeStart(TestCase):
    """cli_node_start must hard-error, not prompt, when no name/config is given."""

    def test_no_name_or_config_errors_without_prompting(self):
        runner = CliRunner()
        with patch("vantage6.node.cli.node.node") as mock_node:
            result = runner.invoke(cli_node_start, [])
        self.assertEqual(result.exit_code, 1)
        mock_node.run.assert_not_called()

    def test_nonexistent_name_errors_without_prompting(self):
        runner = CliRunner()
        with (
            patch("vantage6.node.cli.node.node") as mock_node,
            patch(
                "vantage6.node.cli.node.NodeContext.config_exists",
                return_value=False,
            ),
        ):
            result = runner.invoke(cli_node_start, ["--name", "does-not-exist"])
        self.assertEqual(result.exit_code, 1)
        mock_node.run.assert_not_called()

    def test_existing_name_starts_the_node(self):
        runner = CliRunner()
        with (
            patch("vantage6.node.cli.node.node") as mock_node,
            patch("vantage6.node.cli.node.NodeContext") as mock_context_class,
        ):
            mock_context_class.config_exists.return_value = True
            result = runner.invoke(cli_node_start, ["--name", "my-node"])
        self.assertEqual(result.exit_code, 0)
        mock_context_class.config_exists.assert_called_once_with("my-node", False)
        mock_node.run.assert_called_once_with(mock_context_class.return_value)

    def test_explicit_config_path_bypasses_name_lookup_entirely(self):
        # --config bypasses config_exists() entirely; this is intentional.
        runner = CliRunner()
        with (
            patch("vantage6.node.cli.node.node") as mock_node,
            patch(
                "vantage6.node.cli.node.NodeContext", spec=True
            ) as mock_context_class,
        ):
            result = runner.invoke(
                cli_node_start, ["--config", "/mnt/config/my-node.yaml"]
            )
        self.assertEqual(result.exit_code, 0)
        mock_context_class.config_exists.assert_not_called()
        mock_node.run.assert_called_once()

    def test_dockerized_flag_selects_docker_node_context(self):
        runner = CliRunner()
        with (
            patch("vantage6.node.cli.node.node") as mock_node,
            patch("vantage6.node.cli.node.DockerNodeContext") as mock_docker_ctx,
        ):
            result = runner.invoke(
                cli_node_start,
                ["--config", "/mnt/config/my-node.yaml", "--dockerized"],
            )
        self.assertEqual(result.exit_code, 0)
        mock_docker_ctx.assert_called_once()
        mock_node.run.assert_called_once()
