import click
import logging

from functools import wraps
from pytaskmanager import server
from pytaskmanager.server import db
from pytaskmanager import util
from pytaskmanager.util.find_files import get_config_location
from pytaskmanager.server import fixtures


# TODO maybe make a constants/settings file? and put this fellow in there
APPNAME = 'pytaskmanager'


# ------------------------------------------------------------------------------
# context decorator
# see: https://github.com/pallets/click/issues/108
# ------------------------------------------------------------------------------
# TODO do we need the force_create to be an option too?
def set_context(return_context=False):
    def real_set_context(func):

        # add option decorators
        @click.option('-n', '--name', default='default', help='server instance to use')
        @click.option('-c', '--config', default=None, help='filename of config file; overrides --name if provided')
        @click.option('-e', '--environment', default='test', help='database environment to use')
        @wraps(func)
        def func_with_context(name, config, environment, *args, **kwargs):
            # initialize application class
            ctx = util.AppContext(APPNAME, 'server', name)

            # load configuration and initialize logging system
            cfg_filename = get_config_location(ctx, config, force_create=False)
            ctx.init(cfg_filename, environment)

            # initialize database from environment
            uri = ctx.get_database_location()
            db.init(uri)

            # click.echo(args)
            if return_context:
                return func(ctx, *args, **kwargs)
            else:
                return func(*args, **kwargs)
        return func_with_context
    return real_set_context


# ------------------------------------------------------------------------------
# ptm server
# ------------------------------------------------------------------------------
@click.group(name='server')
def cli_server():
    """Subcommand `ptm server`."""
    pass


@cli_server.command(name='start')
@click.option('--ip', type=str, help='ip address to listen on')
@click.option('-p', '--port', type=int, help='port to listen on')
@click.option('--debug/--no-debug', default=True, help='run server in debug mode (auto-restart)')
@set_context(return_context=True)  # adds options (--name, --config, --environment)
def cli_server_start(ctx, ip, port, debug):
    """Start the server."""
    # click.echo("Starting server ...")
    # click.echo(f"  ip: {ip}")
    # click.echo(f"  port: {port}")
    # Load the flask.Resources
    server.init_resources(ctx)
    
    # Run the server
    ip = ip or ctx.config['ip'] or '127.0.0.1'
    port = port or ctx.config['port'] or 5000
    server.run(ctx, ip, port, debug=debug)


@cli_server.command(name='config_location')
@click.option('-n', '--name', default='default', help='server instance to use')
def cli_server_configlocation(name):
    """Print the location of the default config file."""
    ctx = util.AppContext(APPNAME, 'server', name)
    cfg_filename = get_config_location(ctx, config=None, force_create=False)
    click.echo('{}'.format(cfg_filename))


@cli_server.command(name='load_fixtures')
@set_context(return_context=True)  # adds options (--name, --config, --environment)
def cli_server_load_fixtures(ctx):
    """Load fixtures for testing."""
    fixtures.init(ctx)
    fixtures.create()


# user
@cli_server.command(name='add_user')
@click.option('-u', '--username', prompt='Username', help='username')
@click.option('-p', '--password', prompt='Password', hide_input=True)
@click.option('-f', '--firstname', prompt='First-name', help='first name of the user')
@click.option('-l', '--lastname', prompt='Last-name', help='family name of the user')
@click.option('-l', '--organization_id', prompt='Organization Id', help='organization id to which te user belongs')
@set_context()  # adds options (--name, --config, --environment)
def cli_server_add_user(username, password, firstname, lastname, organization_id):
    """add super-user in a specific environment and configuration"""
    log = logging.getLogger('ptm')

    # make sure the username does not exist yet
    while db.User.username_exists(username):
        log.debug('Username: "{}", is already in the database'.format(username))
        username = click.prompt('Username already exists, please enter a new username')

    # create new user

    user = db.User(
        username=username,
        password=password,  # TODO move this
        firstname=firstname,
        lastname=lastname,
        organization_id=organization_id,
        roles='admin'
    )


    # write to database
    log.info('Username "{}" is added to the database'.format(username))
    user.save()


@cli_server.command(name='update_user')
@click.argument('username')
@click.option('-u', '--new_username', default=None, help='username to update')
@click.option('-p', '--password', default=False, is_flag=True, hide_input=True)
@click.option('-f', '--firstname', default=None, help='first name of the user')
@click.option('-l', '--lastname', default=None, help='family name of the user')
@click.option('-r', '--role', default=None, help='role of the user')
@click.option('-r', '--organization_id', default=None, help='role of the user')
@set_context()  # adds options (--name, --config, --environment)
def cli_server_update_user(username, new_username, password, firstname, lastname, role, organization_id):
    """update user in specific environment and configuration"""
    log = logging.getLogger('ptm')

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
    if organization_id:  # TODO make this a human-readable input
        log.debug('organization_id updated from {} to {}'.format(user.organization_id, organization_id))
        user.organization_id = organization_id

    # store updated fields
    user.save()


@cli_server.command(name='user_list')
@click.option('-r', '--role', default='All')
@set_context()  # adds options (--name, --config, --environment)
def cli_server_user_list(role):
    """list users of specific environment and configuration"""
    log = logging.getLogger('ptm')

    # retrieve user-list from database
    # TODO filter on roles (?) maybe others too
    users = db.User.get_user_list(None)

    # display users
    # TODO this fails if a field is missing, maybe raise an error if this is the case?
    click.echo('\n')
    for user in users:
        click.secho('{username:45} {organization:30} {role:30}'.format(
            organization=user.organization.name,
            username=user.username,
            role=user.roles))


@cli_server.command(name='remove_user')
@click.argument('username')
@set_context()  # adds options (--name, --config, --environment)
def cli_server_remove_user(username):
    """remove user"""
    log = logging.getLogger('ptm')

    # check if user exists, and delete if this is the case
    if db.User.username_exists(username):
        user = db.User.getByUsername(username)
        user.delete()
        log.info('user: "{}" has been removed from the database'.format(username))
    else:
        log.warning('username "{}" does not exist'.format(username))
