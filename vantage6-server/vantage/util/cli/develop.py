import click
import logging
import questionary as q
import IPython
import os
import errno
import yaml
import subprocess

from functools import wraps
from pathlib import Path
from traitlets.config import get_config

from vantage import server, util, constants
from vantage.server import db, shell
from vantage.server.controller import fixture
from vantage.util.context import ( get_config_location, 
    select_configuration_questionaire, configuration_wizard ) 

from vantage.server.cli.server import cli_server_import



@click.group(name='develop')
def cli_develop():
    """Subcommand `ptm server`."""
    pass

#
#   start
#
@cli_develop.command(name='start')
def cli_develop_start():
    """Start development environment.
    
    Starts a server and node configs. 
    """

    dev_folder = constants.PACAKAGE_FOLDER / constants.APPNAME / \
        "_data" / "dev"
    
    node_a_config = dev_folder / "node_a.yaml"
    node_b_config = dev_folder / "node_b.yaml"
    server_config = dev_folder / "server.yaml"
    server_fixtures = dev_folder / "fixtures.yaml"
    
    # subprocess.call(["start", "ppserver", "start", "--name", "Test 3, we are going to make it happen"])
    
    subprocess.call(["ppserver", "import", str(server_fixtures), "--config", str(server_config), "--drop-all"], shell=False)
    
    os.system(f"start cmd /K ppserver start --config {server_config}")
    os.system(f"start cmd /K ppserver shell --config {server_config}")
    os.system(f"start cmd /K ppnode start --config {node_a_config}")
    os.system(f"start cmd /K ppnode start --config {node_b_config}")
    