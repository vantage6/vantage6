import os
import collections
import yaml
import logging

from pathlib import Path
from schema import Schema, And, Or, Use, Optional

class Configuration(collections.UserDict):
    """Base to contains a single configuration."""
    
    VALIDATORS = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def __setitem__(self, key, value):
        """ Validation of a single item when put
        """
        # assert key in self.VALIDATORS.keys(), "Invalid Key!"
        schema = Schema(self.VALIDATORS.get(key,lambda x: True), ignore_extra_keys=True)
        assert schema.is_valid(value), f"Invalid Value! {value} for {schema}"
        super().__setitem__(key, value)
   
    def __getitem__(self, key):
        if key in self.data:
            return super().__getitem__(key)
        else:
            raise KeyError(key)

    @property
    def is_valid(self):
        return Schema(self.VALIDATORS, ignore_extra_keys=True).is_valid(self.data)
            

class ServerConfiguration(Configuration):

    VALIDATORS = {
        "description": Use(str),
        "ip": Use(str) ,
        "port": Use(int),  
        "api_path": Use(str),
        "uri": Use(str),
        "allow_drop_all": Use(bool),
        "logging":{
            "level": And(Use(str), lambda l: l in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")),
            "file": Use(str),
            "use_console": Use(bool),
            "backup_count": And(Use(int), lambda n: n > 0),
            "max_size": And(Use(int), lambda b: b > 16),
            "format": Use(str),
            "datefmt": Use(str)
        }
    }
    

class NodeConfiguration(Configuration):
    
    VALIDATORS = {
        "api_key": And(Use(str), len),
        "server_url": Use(str),
        "port": Or(Use(int), None),
        "task_dir": Use(str),
        "databases": {Use(str):Use(str)},
        "api_path": Use(str),
        "logging": {
            "level": And(Use(str), lambda l: l in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")),
            "file": Use(str),
            "use_console": Use(bool),
            "backup_count": And(Use(int), lambda n: n > 0),
            "max_size": And(Use(int), lambda b: b > 16),
            "format": Use(str),
            "datefmt": Use(str)
        },
        "encryption": {
            "disabled": bool,
            Optional("private_key"): Use(str)
        }
    }

class TestConfiguration(Configuration):

    VALIDATORS = {
        # "api_key": And(Use(str), len),
        # "logging": {
        #     "level": And(Use(str), lambda l: l in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NONE")),
        #     "file": Use(str),
        #     "use_console": Use(bool),
        #     "backup_count": And(Use(int), lambda n: n > 0),
        #     "max_size": And(Use(int), lambda b: b > 16),
        #     "format": Use(str),
        #     "datefmt": Use(str)
        # }
    }
    
    
class ConfigurationManager(object):
    """Class to maintain valid configuration settings.

    A configuration file contains at top level an `application` and/or 
    `environments` key. The `environments` key can contain up to four 
    keys: `dev`, `test`, `acc`, `prod`. e.g.:
    application:
        ...
    environments:
        dev:
            ...
        test:
            ...
        acc:
            ...
        prod:
            ...
    
    Note that this structure is the same for the node and server.
    """
    ENVS = ("application", "prod", "acc", "test", "dev")

    def __init__(self, conf_class=Configuration, name=None):
        self.application = ""
        self.prod = ""
        self.acc = ""
        self.test = ""
        self.dev = ""
    
        self.name = name
        self.conf_class = conf_class
        
    def put(self, env:str, config: dict):
        assert env in self.ENVS
        configuration = self.conf_class(config)
        # only set valid configs
        if configuration.is_valid:
            self.__setattr__(env, configuration)
        # else:
        #      print(f"config={config}")
        #      print(self.conf_class)
        
    def get(self, env:str):
        assert env in self.ENVS
        return self.__getattribute__(env)

    @property
    def is_empty(self):
        return not (self.application or self.prod or self.acc \
            or self.test or self.dev)

    @property
    def environments(self): 
        return {"prod":self.prod, "acc":self.acc, "test":self.test, 
            "dev":self.dev, "application": self.application}

    @property
    def has_application(self):
        return bool(self.application)

    @property
    def has_environments(self):
        return any([bool(env) for key, env in self.environments])
    
    @property
    def available_environments(self):
        return [key for key, env in self.environments.items() if env]
    
    def _get_environment_from_dict(self, d, e):
        assert e in self.ENVS
        if e == "application":
            return d.get("application",{})  
        else:
            return d.get("environments",{}).get(e,{})
           
    def load(self, path):
        with open(str(path), 'r') as f:
            config = yaml.safe_load(f)
        
        for env in self.ENVS:
            self.put(env, self._get_environment_from_dict(config, env))
    
    @classmethod
    def from_file(cls, path, conf_class=Configuration):
        name = Path(path).stem
        assert name, f"Name could not be extracted from filepath={path}"
        conf = cls(name=name, conf_class=conf_class)
        conf.load(path)
        return conf


    def save(self, path):

        config = {"application": dict(self.application), "environments": {
            "prod": dict(self.prod), "acc": dict(self.acc), "test": dict(self.test), 
            "dev": dict(self.dev)}}
    
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)


class NodeConfigurationManager(ConfigurationManager):
    
    def __init__(self, name, *args, **kwargs):
        super().__init__(conf_class=NodeConfiguration, name=name)

    @classmethod
    def from_file(cls, path):
        return super().from_file(path, conf_class=NodeConfiguration)


class ServerConfigurationManager(ConfigurationManager):
    
    def __init__(self, name, *args, **kwargs):
        super().__init__(conf_class=ServerConfiguration, name=name)

    @classmethod
    def from_file(cls, path):
        return super().from_file(path, conf_class=ServerConfiguration)


class TestingConfigurationManager(ConfigurationManager):

    def __init__(self, name, *args, **kwargs):
        super().__init__(conf_class=TestConfiguration, name=name)

    @classmethod
    def from_file(cls, path):
        return super().from_file(path, conf_class=TestConfiguration)