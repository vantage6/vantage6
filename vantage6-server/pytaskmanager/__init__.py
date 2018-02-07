import click

import os
import shutil
import yaml

here = os.path.abspath(os.path.dirname(__file__))
__version__ = ''

with open(os.path.join(here, 'VERSION')) as fp:
    __version__ = fp.read()



from . import server
from .server import fixtures
from . import client
from . import utest

@click.group()
def cli():
    """Main entry point for CLI scripts."""
    pass


@cli.command()
@click.option('-c', '--config', default=None, type=click.Path(), help='location of the config file')
def test(config):
    utest.run(config)


# ------------------------------------------------------------------------------
# ptm run
# ------------------------------------------------------------------------------
@cli.group()
def run():
    pass

@run.command(name='server')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('-c', '--config', default='config.yaml', help='location of the config file')
@click.option('--ip', default='0.0.0.0', help='ip address to listen on')
@click.option('-p', '--port', default=5000, help='port to listen on')
@click.option('--debug/--no-debug', default=True, help='run server in debug mode (auto-restart)')
def run_server(environment, config, ip, port, debug):
    server.init_resources()
    server.run(environment, config, ip, port, debug=debug)


@run.command(name='client')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('-c', '--config', default='config.yaml', help='location of the config file')
def run_client(environment, config):
    client.run(environment, config)


# ------------------------------------------------------------------------------
# ptm create
# ------------------------------------------------------------------------------
@cli.group()
def create():
    pass

pparams = {
    'exists': False, 
    'file_okay': False, 
    'dir_okay': True,
}

@create.command(name='client')
@click.option('--location', prompt='Please enter a folder name', type=click.Path(*pparams))
def create_client(location):    
    click.echo("create_client")
    click.echo(click.format_filename(location))


@create.command(name='server')
@click.option('--location', prompt='Please enter a folder name', type=click.Path(**pparams))
def create_server(location):
    click.echo("Creating directory for server (instance): {}".format(location))
    os.makedirs(location, exist_ok=True)

    src = os.path.join(here, '_data', 'server_config_skeleton.yaml')
    dst = os.path.join(location, 'config.yaml')
    shutil.copy(src, dst)



# ------------------------------------------------------------------------------
# ptm load
# ------------------------------------------------------------------------------
@cli.group()
def load():
    pass

@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('-c', '--config', default='config.yaml', help='location of the config file')
@load.command(name='fixtures')
def cli_fixtures(environment, config):
    fixtures.init(environment, config)
    fixtures.create()

