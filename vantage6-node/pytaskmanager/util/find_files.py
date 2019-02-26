import click
import sys
import os
import shutil
import yaml


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
        
        # TODO let's remove this
        if config and not force_create:
            click.echo("Configuration file '{}' does not exist and '--force-create' not specified!".format(filename))
            click.echo("Aborting ...")
            sys.exit(1)

        # make sure the config directory exists
        dirname = os.path.dirname(filename)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        # copy a default config file to the config location
        skeleton_file = ctx.instance_type + "_config_skeleton.yaml"
        src = os.path.join(ctx.package_data_dir(), skeleton_file)
        dst = os.path.join(filename)
        shutil.copy(src, dst)

        # set the logging file to the name of the instance 
        if ctx.instance_type == 'server':
             # load current config
            with open(dst, 'r') as fp:
                cfg = yaml.load(fp)
            
            # update logging filename for all enviroments
            for environment in cfg['environments'].items():
                cfg[environment]['logging']['file'] = ctx.instance_name + '.log'

            # write back to the config
            with open(dst, 'w') as fp:
                yaml.dump(cfg, fp)

    return filename
