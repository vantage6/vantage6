import click
import sys
import os
import shutil
import yaml
import questionary as q

from pathlib import Path
from schema import Schema, And, Or, Use, Optional

from vantage import util
# from vantage.util import AppContext
from vantage.util.Configuration import ( ConfigurationManager, 
    NodeConfigurationManager, ServerConfigurationManager ) 

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
            "default": "127.0.0.1"
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
            "message": "Database URI:"
        },
        {
            "type": "select", 
            "name": "allow_drop_all",
            "message": "Allowed to drop all tables: ",
            "choices": ["True", "False"]
        }
    ])

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

    return config

def configuration_wizard(instance_type, instance_name, 
    environment="application", system_folders=False):

    # for defaults and where to save the config
    dirs = util.NodeContext.instance_folders(instance_type, 
        instance_name, system_folders)
    
    if instance_type == "node":
        config = node_configuration_questionaire(dirs, instance_name)
    else:
        config = server_configuration_questionaire(dirs, instance_name)
    
    # in the case of an environment we need to add it to the current 
    # configuration. In the case of application we can simply overwrite this 
    # key (although there might be environments present)
    config_file = Path(dirs.get("config")) / (instance_name + ".yaml")
    conf_class = NodeConfigurationManager if instance_type == "node" else \
        ServerConfigurationManager
    
    if Path(config_file).exists():
        config_manager = conf_class.from_file(config_file)
    else:
        config_manager = conf_class(instance_name)

    config_manager.put(environment, config)
    config_manager.save(config_file)

    return config_file

# TODO deprecated, still used by server instance, should be replaced
# by some sort of questionaire
def get_config_location(ctx, config, force_create):
    """Ensure configuration file exists and return its location."""
    return config if config else ctx.config_file
    
def select_configuration_questionaire(instance_type, system_folders):
    """Asks which configuration the user want to use
    
    It shows only configurations that are in the default folder.
    """
    Context = util.NodeContext if instance_type == "node" else \
        util.ServerContext
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