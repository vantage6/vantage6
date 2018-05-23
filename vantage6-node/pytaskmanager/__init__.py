import click

import sys
import os
import shutil
import yaml
import logging

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
from sqlalchemy.orm.exc import NoResultFound

APPNAME = 'pytaskmanager'

# ------------------------------------------------------------------------------
# helper functions
# ------------------------------------------------------------------------------


def get_config_location(ctx, config, force_create):
    """Ensure configuration file exists and return its location."""
    if config is None:
        # Get the location of config.yaml if not provided
        filename = ctx.config_file
    else:
        # Use the config file provided as argument
        filename = config

    # Check that the config file exists and create it if necessary, but
    # only if it was not explicitly provided!
    if not os.path.exists(filename):
        # We will always create a configuration file at the default location
        # when necessary.
        if config and not force_create:
            click.echo("Configuration file '{}' does not exist and '--force-create' not specified!".format(filename))
            click.echo("Aborting ...")
            sys.exit(1)

        # Make sure the directory exists
        dirname = os.path.dirname(filename)

        if dirname:
            os.makedirs(dirname, exist_ok=True)

        # Copy a default config file
        if ctx.instance_type == 'server':
            skeleton_file = 'server_config_skeleton.yaml'
        elif ctx.instance_type == 'client':
            skeleton_file = 'client_config_skeleton.yaml'
        elif ctx.instance_type == 'unittest':
            skeleton_file = 'unittest_config_skeleton.yaml'

        src = os.path.join(here, '_data', skeleton_file)
        dst = os.path.join(filename)
        shutil.copy(src, dst)

        if ctx.instance_type == 'server':
            with open(dst, 'r') as fp:
                cfg = yaml.load(fp)
                print('-' * 80)
                print(cfg)
                print('-' * 80)

            cfg['application']['logging']['file'] = ctx.instance_name + '.log'

            with open(dst, 'w') as fp:
                yaml.dump(cfg, fp)

    return filename


def set_api_key_in_client_config(cfg_filename, api_key=None):
    """"Make sure an API is present in the client configuration file"""

    with open(cfg_filename, 'r') as f:
        config = yaml.load(f)

    # get the api key from the config file, this could be an empty field
    config_api_key = config['application']['api_key']

    # check if api-key is not set in the config file and not provided
    if not config_api_key and not api_key:
        api_key = click.prompt("please enter API-key", type=str)

    if api_key:

        config['application']['api_key'] = api_key

        with open(cfg_filename, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)



@click.group()
def cli():
    """Main entry point for CLI scripts."""
    pass


# ------------------------------------------------------------------------------
# ptm test
# ------------------------------------------------------------------------------
@cli.command(name='test')
@click.option('-c', '--config', default=None, type=click.Path(), help='location of the config file')
def cli_test(config):
    """Run unit tests."""
    ctx = util.AppContext(APPNAME, 'unittest')
    cfg_filename = get_config_location(ctx, config=None, force_create=False)
    ctx.init(cfg_filename)
    utest.run()


# ------------------------------------------------------------------------------
# ptm server
# ------------------------------------------------------------------------------
@cli.group(name='server')
def cli_server():
    """Subcommand `ptm server`."""
    pass


@cli_server.command(name='start')
@click.option('-n', '--name', default='default', help='server instance to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('--ip', default='0.0.0.0', help='ip address to listen on')
@click.option('-p', '--port', default=5000, help='port to listen on')
@click.option('--debug/--no-debug', default=True, help='run server in debug mode (auto-restart)')
@click.option('--force-create', is_flag=True, help='Force creation of config file')
def cli_server_start(name, config, environment, ip, port, debug, force_create):
    """Start the server."""
    click.echo("Starting server ...")
    ctx = util.ServerContext(APPNAME, 'default')
    # Load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create)
    ctx.init(cfg_filename, environment)

    # Load the flask.Resources
    server.init_resources(ctx)
    # Run the server
    server.run(ctx, ip, port, debug=debug)


@cli_server.command(name='config_location')
@click.option('-n', '--name', default='default', help='server instance to use')
def cli_server_configlocation(name):
    """Print the location of the default config file."""
    ctx = util.AppContext(APPNAME, 'server', name)
    cfg_filename = get_config_location(ctx, config=None, force_create=False)
    click.echo('{}'.format(cfg_filename))


# TODO this functionality is replaced by 'ptm server update_user'
@cli_server.command(name='passwd')
@click.option('-n', '--name', default='default', help='server instance to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('-p', '--password', prompt='Password', hide_input=True)
def cli_server_passwd(name, config, environment, password):
    """Set the root password."""
    log = logging.getLogger('ptm')

    # initialize application
    ctx = util.AppContext(APPNAME, 'server', name)

    # Load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create=False)
    ctx.init(cfg_filename, environment)

    uri = ctx.get_database_location()
    db.init(uri)

    try:
        root = db.User.getByUsername('root')
    except Exception as e:
        log.info("Creating user root")
        root = db.User(username='root')

    log.info("Setting password for root")
    root.set_password(password)
    root.save()

    log.info("[DONE]")


@cli_server.command(name='load_fixtures')
@click.option('-n', '--name', default='default', help='server instance to use')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
def cli_server_load_fixtures(name, environment, config):
    """Load fixtures for testing."""
    click.echo("Loading fixtures.")
    ctx = util.AppContext(APPNAME, 'server', name)

    # Load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create=False)
    ctx.init(cfg_filename, environment)

    fixtures.init(ctx)
    fixtures.create()


# user
@cli_server.command(name='add_user')
@click.option('-n', '--name', default='default', help='server instance to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('-u', '--username', prompt='Username', help='username')
@click.option('-p', '--password', prompt='Password', hide_input=True)
@click.option('-f', '--firstname', prompt='First-name', help='first name of the user')
@click.option('-l', '--lastname', prompt='Last-name', help='family name of the user')
@click.option('-l', '--organization_id', prompt='Organization Id', help='organization id to which te user belongs')
def cli_server_add_user(name, config, environment, username, password, firstname, lastname, organization_id):
    """add super-user"""
    log = logging.getLogger('ptm')

    # initialize application class
    ctx = util.AppContext(APPNAME, 'server', name)

    # load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create=False)
    ctx.init(cfg_filename, environment)

    # initialize database from environment
    uri = ctx.get_database_location()
    db.init(uri)

    # make sure the username does not exist yet
    while db.User.username_exists(username):
        log.debug('Username: "{}", is already in the database'.format(username))
        username = click.prompt('Username already exists, please enter a new username')

    # create new user
    user = db.User(
        username=username,
        password=password,
        firstname=firstname,
        lastname=lastname,
        organization_id=organization_id,
        roles='admin'
    )

    # write to database
    log.info('Username "{}" is added to the database'.format(username))
    user.save()


@cli_server.command(name='update_user')
@click.option('-n', '--name', default='default', help='server instance to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('-u', '--username', prompt='Username you want to change', help='username to update')
@click.option('-u', '--new_username', default=None, help='username to update')
@click.option('-p', '--password', default=False, is_flag=True, hide_input=True)
@click.option('-f', '--firstname', default=None, help='first name of the user')
@click.option('-l', '--lastname', default=None, help='family name of the user')
@click.option('-r', '--role', default=None, help='role of the user')
@click.option('-r', '--organization_id', default=None, help='role of the user')
def cli_server_update_user(name, config, environment, username, new_username, password, firstname, lastname, role, organization_id):
    """update user"""
    log = logging.getLogger('ptm')

    # initialize application class
    ctx = util.AppContext(APPNAME, 'server', name)

    # load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create=False)
    ctx.init(cfg_filename, environment)

    # initialize database from environment
    uri = ctx.get_database_location()
    db.init(uri)

    # get user
    while not db.User.username_exists(username):
        click.echo('Username {} not found in the database'.format(username))
        username = click.prompt('Enter username you wish to change')
    user = db.User.getByUsername(username)

    # modify fields
    if new_username:
        log.debug('username updated from {} to {}'.format(user.username, new_username))
        user.username = new_username
    if password:
        new_password = click.prompt('Please enter new password', hide_input=True)
        log.debug('password updated')
        user.set_password(new_password)
    if firstname:
        log.debug('firstname updated from {} to {}'.format(user.firstname, firstname))
        user.firstname = firstname
    if lastname:
        log.debug('lastname updated from {} to {}'.format(user.lastname, lastname))
        user.lastname = lastname
    if role:
        log.debug('roles updated from {} to {}'.format(user.roles, role))
        user.roles = role
    if organization_id:  # TODO make this a human readable input
        log.debug('organization_id updated from {} to {}'.format(user.organization_id, organization_id))
        user.organization_id = organization_id

    # store updated fields
    user.save()


@cli_server.command(name='user_list')
@click.option('-n', '--name', default='default', help='server instance to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('-r', '--role', default='All')
def cli_server_user_list(name, config, environment, role):
    """list users"""
    log = logging.getLogger('ptm')

    # initialize application class
    ctx = util.AppContext(APPNAME, 'server', name)

    # load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create=False)
    ctx.init(cfg_filename, environment)

    # initialize database from environment
    uri = ctx.get_database_location()
    db.init(uri)

    # retrieve user-list from database
    users = db.User.get_user_list(None)  # TODO filter on roles (?) maybe others too

    # display users
    click.echo('\n')
    for user in users:
        click.secho('{username:45} {organization:30} {role:30}'.format(
            organization=user.organization.name,
            username=user.username,
            role=user.roles))


@cli_server.command(name='remove_user')
@click.option('-n', '--name', default='default', help='server instance to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
@click.option('-e', '--environment', default='test', help='database environment to use')
@click.option('-u', '--username', prompt='Username', help='username of user to remove')
def cli_server_remove_user(name, config, environment, username):
    """remove user"""
    log = logging.getLogger('ptm')

    # initialize application class
    ctx = util.AppContext(APPNAME, 'server', name)

    # load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create=False)
    ctx.init(cfg_filename, environment)

    # initialize database from environment
    uri = ctx.get_database_location()
    db.init(uri)

    if db.User.username_exists(username):
        click.echo(db.User.remove_user(username))
        log.info('user: "{}" has been removed from the database'.format(username))
    else:
        log.warning('username "{}" does not exist'.format(username))


# ------------------------------------------------------------------------------
# ptm client
# ------------------------------------------------------------------------------
@cli.group(name='client')
def cli_client():
    """Subcommand `ptm client`."""
    pass


@cli_client.command(name='config_location')
@click.option('-n', '--name', default='default', help='client instance to use')
def cli_server_configlocation(name):
    """Print the location of the default config file."""
    ctx = util.AppContext(APPNAME, 'client', name)
    cfg_filename = get_config_location(ctx, config=None, force_create=False)
    click.echo('{}'.format(cfg_filename))


@cli_client.command(name='start')
@click.option('-n', '--name', default='default', help='client instance to use')
@click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
@click.option('-a', '--api_key', default=None, help='ptm server api-key')
def cli_client_start(name, config, api_key):
    """Start the client."""
    ctx = util.AppContext(APPNAME, 'client', name)

    # Load configuration and initialize logging system
    cfg_filename = get_config_location(ctx, config, force_create=False)

    # provide api key to the configuration file
    set_api_key_in_client_config(cfg_filename, api_key)

    ctx.init(cfg_filename)

    # Run the client
    client.run(ctx)
