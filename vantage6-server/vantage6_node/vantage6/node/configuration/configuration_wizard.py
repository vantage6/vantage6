import click
import sys
import os
import shutil
import yaml
import questionary as q

from pathlib import Path
from schema import Schema, And, Or, Use, Optional

from vantage6.node import util

from vantage6.node.context import NodeContext
from vantage6.node.configuration.configuration_manager import (
    ConfigurationManager,
    NodeConfigurationManager, 
    ServerConfigurationManager
)


def node_configuration_questionaire(dirs, instance_name):
    """Questionary to generate a config file for the node instance."""

    config = q.prompt([
        {
            "type": "text",
            "name": "api_key",
            "message": "Enter given api-key:"
        },
        {
            "type": "text",
            "name": "server_url",
            "message": "The base-URL of the server:",
            "default": "http://localhost"
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
            "name": "task_dir",
            "message": "Task directory path:",
            "default": str(dirs["data"])
        }
    ])
    
    config["databases"] = q.prompt([
        {
            "type": "text",
            "name": "default",
            "message": "Default database path:"
        }
    ])
    i = 1
    while q.confirm("Do you want to add another database?").ask():
        q2 = q.prompt([
        {
            "type": "text",
            "name": "label",
            "message": "Enter the label for the database:",
            "default": f"database_{i}"
        },
        {
            "type": "text",
            "name": "path",
            "message": "The path of the database file:",
            "default": str(
                Path(config.get("databases").get("default")).parent)
        }])
        config["databases"][q2.get("label")] = q2.get("path")
        i+=1


    res = q.select("Which level of logging would you like?",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"]
    ).ask()

    config["logging"] = {
        "level": res,
        "file": f"{instance_name}.log",
        "use_console": True,
        "backup_count":5,
        "max_size": 1024,
        "format": "%(asctime)s - %(name)-14s - %(levelname)-8s - %(message)s",
        "datefmt": "%H:%M:%S"
    }

    disable_encryption = q.select("Disable encryption?", 
        choices=["false", "true"]).ask()

    private_key = "" if disable_encryption == "true" else \
        q.text("Path to private key file:").ask()

    config["encryption"] = {
        "disabled": disable_encryption == "true",
        "private_key": private_key
    }

    return config

def configuration_wizard(instance_name, 
    environment="application", system_folders=False):

    # for defaults and where to save the config
    dirs = NodeContext.instance_folders("node", instance_name, system_folders)
    
    # invoke questionaire to create configuration file
    config = node_configuration_questionaire(dirs, instance_name)
    
    # in the case of an environment we need to add it to the current 
    # configuration. In the case of application we can simply overwrite this 
    # key (although there might be environments present)
    config_file = Path(dirs.get("config")) / (instance_name + ".yaml")
    
    if Path(config_file).exists():
        config_manager = NodeConfigurationManager.from_file(config_file)
    else:
        config_manager = NodeConfigurationManager(instance_name)

    config_manager.put(environment, config)
    config_manager.save(config_file)

    return config_file
    
def select_configuration_questionaire(system_folders):
    """Asks which configuration the user want to use
    
    It shows only configurations that are in the default folder.
    """
    Context = NodeContext
    configs, f = Context.available_configurations(system_folders)

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