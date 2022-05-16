import questionary as q
import uuid

from pathlib import Path

from vantage6.cli.context import ServerContext
from vantage6.server.configuration.configuration_manager import (
    ServerConfigurationManager
)


def server_configuration_questionaire(dirs, instance_name):
    """Questionary to generate a config file for the node instance."""

    config = q.prompt([
        {
            "type": "text",
            "name": "description",
            "message": "Enter a human-readable description:"
        },
        {
            "type": "text",
            "name": "ip",
            "message": "ip:",
            "default": "0.0.0.0"
        },
        {
            "type": "text",
            "name": "port",
            "message": "Enter port to which the server listens:",
            "default": "5000"
        },
        {
            "type": "text",
            "name": "api_path",
            "message": "Path of the api:",
            "default": "/api"
        },
        {
            "type": "text",
            "name": "uri",
            "message": "Database URI:",
            "default": "sqlite:///default.sqlite"
        },
        {
            "type": "select",
            "name": "allow_drop_all",
            "message": "Allowed to drop all tables: ",
            "choices": ["True", "False"]
        }
    ])

    res = q.select(
        "Which level of logging would you like?",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"]
    ).ask()

    constant_jwt_secret = q.confirm("Do you want a constant JWT secret?").ask()
    if constant_jwt_secret:
        config["jwt_secret_key"] = str(uuid.uuid1())

    config["logging"] = {
        "level": res,
        "file": f"{instance_name}.log",
        "use_console": True,
        "backup_count": 5,
        "max_size": 1024,
        "format": "%(asctime)s - %(name)-14s - %(levelname)-8s - %(message)s",
        "datefmt": "%Y-%m-%d %H:%M:%S"
    }

    return config


def configuration_wizard(instance_name, environment, system_folders):

    # for defaults and where to save the config
    dirs = ServerContext.instance_folders("server", instance_name,
                                          system_folders)

    # prompt questionaire
    config = server_configuration_questionaire(dirs, instance_name)

    # in the case of an environment we need to add it to the current
    # configuration. In the case of application we can simply overwrite this
    # key (although there might be environments present)
    config_file = Path(dirs.get("config")) / (instance_name + ".yaml")

    # check if configuration already exists
    if Path(config_file).exists():
        config_manager = ServerConfigurationManager.from_file(config_file)
    else:
        config_manager = ServerConfigurationManager(instance_name)

    # save the new comfiguration
    config_manager.put(environment, config)
    config_manager.save(config_file)

    return config_file


# TODO deprecated, still used by server instance, should be replaced
# by some sort of questionaire
def get_config_location(ctx, config, force_create):
    """Ensure configuration file exists and return its location."""
    return config if config else ctx.config_file


def select_configuration_questionaire(system_folders):
    """Asks which configuration the user want to use

    It shows only configurations that are in the default folder.
    """
    configs, f = ServerContext.available_configurations(system_folders)

    # each collection (file) can contain multiple configs. (e.g. test,
    # dev)
    choices = []
    for config_collection in configs:
        envs = config_collection.available_environments
        for env in envs:
            choices.append(q.Choice(
                title=f"{config_collection.name:25} {env}",
                value=(config_collection.name, env)))

    if not choices:
        raise Exception("No configurations could be found!")

    # pop the question
    name, env = q.select("Select the configuration you want to use:",
                         choices=choices).ask()

    return name, env
