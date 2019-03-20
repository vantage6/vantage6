# TODO work progress...
import logging
import unittest

from pathlib import Path
from click.testing import CliRunner
from prompt_toolkit.input.defaults import create_pipe_input

from pytaskmanager.util import NodeContext, TestContext
from pytaskmanager.cli.node import ( cli_node_files, cli_node_list, 
    cli_node_new_configuration, cli_node_start )

# log = logging.getLogger(__name__.split(".")[-1])
# log.level = logging.CRITICAL


class TestNodeCLI(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()
        self.config_name = "testnodeconfiguration"

        # create configuration at 'official'-user location
        # TODO asdas
        ctx = NodeContext.from_external_config_file(
            TestContext.test_data_location() / "node_config_skeleton.yaml",
            "application", False
        )
        
        # store the test configuration in the default location
        self.tmp_config_file = ctx.config_dir / (self.config_name + ".yaml")
        ctx.config_manager.save(self.tmp_config_file)

    
    def trearDown(self):
        # clean up the temporary configuration file
        Path(self.tmp_config_file).unlink()

    def test_files_using_name(self):
        """Check that configuration loads without exeptions."""
        # log = logging.getLogger("util")
        # log.level = logging.CRITICAL
        res = self.runner.invoke(cli_node_files, [
            "--name", self.config_name
        ])

        assert not res.exception
        assert res.exit_code == 0 
        assert res.output, "no commandline output, that can't be right..."

    def test_files_using_invalid_name(self):
        """Handles an invalid configuration name."""
        res = self.runner.invoke(cli_node_files, [
            "--name", "some-non-existing-filename"
        ])
        
        assert res.exception 
        



    