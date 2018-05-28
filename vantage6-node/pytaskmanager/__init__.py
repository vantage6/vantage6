import click
import os
import yaml

# Define version and directories *before* importing submodules
here = os.path.abspath(os.path.dirname(__file__))

__version__ = ''
with open(os.path.join(here, 'VERSION')) as fp:
    __version__ = fp.read()


# default parameters for click.Path
pparams = {
    'exists': False,
    'file_okay': False,
    'dir_okay': True,
}

from . import server
from .server import fixtures
from .server import db
from . import client
from . import utest
from . import util
from . import cli

APPNAME = 'pytaskmanager'

#
#
# @click.group()
# def cli():
#     """Main entry point for CLI scripts."""
#     pass
#
#
# # ------------------------------------------------------------------------------
# # ptm test
# # ------------------------------------------------------------------------------
# @cli.command(name='test')
# @click.option('-c', '--config', default=None, type=click.Path(), help='location of the config file')
# def cli_test(config):
#     """Run unit tests."""
#     ctx = util.AppContext(APPNAME, 'unittest')
#     cfg_filename = get_config_location(ctx, config=None, force_create=False)
#     ctx.init(cfg_filename)
#     utest.run()
