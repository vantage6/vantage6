import click
import sys
import os
import shutil
import yaml

# Define version and directories *before* importing submodules
here = os.path.abspath(os.path.dirname(__file__))


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
        elif ctx.instance_type == 'node':
            skeleton_file = 'node_config_skeleton.yaml'
        elif ctx.instance_type == 'unittest':
            skeleton_file = 'unittest_config_skeleton.yaml'

        # TODO relocate this to a config file
        src = os.path.join(here, '..', '_data', skeleton_file)

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
