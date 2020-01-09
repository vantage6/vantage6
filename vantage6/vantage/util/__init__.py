import sys
import os, os.path
import pprint
import vantage.util.Colorer
import logging
import logging.handlers
import appdirs
import yaml
import base64

from schema import SchemaError
from pathlib import Path
from sqlalchemy.engine.url import make_url
from weakref import WeakValueDictionary

import vantage.constants as constants

from vantage.util.Configuration import ( ConfigurationManager, 
    ServerConfigurationManager, NodeConfigurationManager, 
    TestingConfigurationManager ) 


def logger_name(special__name__):
    log_name = special__name__.split('.')[-1]
    if len(log_name) > 14:
        log_name = log_name[:11] + ".."
    return log_name

class Singleton(type):
    _instances = {} #WeakValueDictionary()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super(Singleton, cls).__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class AppContext(metaclass=Singleton):

    INST_CONFIG_MANAGER = ConfigurationManager
    LOGGING_ENABLED = True

    def __init__(self, instance_type, instance_name, system_folders=False,
        environment=constants.DEFAULT_NODE_ENVIRONMENT):
        """instance name is equal to the config-filename..."""

        # lookup system / user directories
        self.name = instance_name
        self.scope = "system" if system_folders else "user"
        self.set_folders(instance_type, instance_name, system_folders)

        # configuration environment, load a single configuration from 
        # entire confiration file (which can contain multiple environments) 
        self.config_file = self.config_dir / (instance_name + ".yaml")
        
        # will load a specific environment in the config_file, this 
        # triggers to set the logging as this is env dependant
        self.environment = environment

        self.log = None

    def set_folders(self, instance_type, instance_name, system_folders):
        dirs = self.instance_folders(instance_type, instance_name, 
            system_folders)
        self.log_dir = dirs.get("log")
        self.data_dir = dirs.get("data")
        self.config_dir = dirs.get("config")
        
    def setup_logging(self):
        """Setup a basic logging mechanism."""
     
        log_config = self.config["logging"]
             
        level = getattr(logging, log_config["level"].upper())
        format_ = log_config["format"] 
        datefmt = log_config.get("datefmt", "")

        # make sure the log-file exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # Create the root logger
        logger = logging.getLogger()
        logger.setLevel(level)
    
        # Create RotatingFileHandler
        rfh = logging.handlers.RotatingFileHandler(
            self.log_file, 
            maxBytes=1024*log_config["max_size"], 
            backupCount=log_config["backup_count"]
        )
        rfh.setLevel(level)
        rfh.setFormatter(logging.Formatter(format_, datefmt))
        logger.addHandler(rfh)
        
        # Check what to do with the console output ...
        if log_config["use_console"]:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(level)
            ch.setFormatter(logging.Formatter(format_, datefmt))
            logger.addHandler(ch)
            
        # Finally, capture all warnings using the logging mechanism.
        logging.captureWarnings(True)

        module_name = __name__.split('.')[-1]
        log = logging.getLogger(module_name)
        
        # Make some history
        log.info("#" * 80)
        log.info(f'#{constants.APPNAME:^78}#')
        log.info("#" * 80)
        log.info(f"Started application {constants.APPNAME} with environment {self.environment}")
        log.info("Current working directory is '%s'" % os.getcwd())
        log.info("Succesfully loaded configuration from '%s'" % self.config_file)
        log.info("Logging to '%s'" % self.log_file)
        self.log = log
    
    def docker_temporary_volume_name(self, run_id):
        return (
            f"{constants.APPNAME}-{self.name}-{self.scope}"
            f"-{run_id}-tmpvol"
        )

    @property
    def docker_container_name(self):
        return f"{constants.APPNAME}-{self.name}-{self.scope}"

    @property
    def docker_network_name(self):
        return f"{constants.APPNAME}-{self.name}-{self.scope}"

    @property
    def log_file(self):
        assert self.config_manager, \
            "Log file unkown as configuration manager not initialized"
            
        if self.config.get("logging"):
            if self.config.get("logging").get("file"):
                return self.log_dir / self.config.get("logging").get("file")
        file_ = f"{self.config_manager.name}-{self.environment}-{self.scope} + .log"
        return self.log_dir / file_

    @property
    def config_file_name(self):
        return self.__config_file.stem

    @property
    def config_file(self):
        return self.__config_file
    
    @config_file.setter
    def config_file(self, path):
        assert Path(path).exists(), f"config {path} not found" 
        self.__config_file = Path(path)
        self.config_manager = self.INST_CONFIG_MANAGER.from_file(path)
        
    @property
    def environment(self):
        return self.__environment
    
    @environment.setter
    def environment(self, env):
        assert self.config_manager, \
            "Environment set before ConfigurationManager is initialized..."
        assert env in self.config_manager.available_environments, \
            f"Requested environment {env} is not found in the configuration"
        self.__environment = env
        self.config = self.config_manager.get(env)
        if self.LOGGING_ENABLED:
            self.setup_logging()

    @classmethod
    def from_external_config_file(cls, path, instance_type, 
        environment=constants.DEFAULT_NODE_ENVIRONMENT, system_folders=False):
        instance_name = Path(path).stem
        self_ = cls.__new__(cls)
        self_.set_folders(instance_type, instance_name, system_folders)
        self_.config_dir = Path(path).parent
        self_.config_file = path
        self_.environment = environment
        return self_

    @classmethod
    def config_exists(cls, instance_type, instance_name, environment=constants.DEFAULT_NODE_ENVIRONMENT, 
        system_folders=False):
        
        # obtain location of config file
        d = appdirs.AppDirs(constants.APPNAME, "")
        config_dir = d.site_config_dir if system_folders else d.user_config_dir
        config_file = Path(config_dir) / instance_type / (instance_name+".yaml")
        if not Path(config_file).exists():
            return False

        # check that environment is present in config-file
        config_manager = cls.INST_CONFIG_MANAGER.from_file(config_file)
        return bool(getattr(config_manager, environment))

    @staticmethod
    def instance_folders(instance_type, instance_name, system_folders):
        d = appdirs.AppDirs(constants.APPNAME, "")
        if system_folders:
            return {
                "log":Path(d.site_data_dir) / instance_type,
                "data":Path(d.site_data_dir) / instance_type / instance_name,
                "config":Path(d.site_config_dir) / instance_type
            }
        else:
            return {
                "log":Path(d.user_log_dir) / instance_type,
                "data":Path(d.user_data_dir) / instance_type / instance_name,
                "config":Path(d.user_config_dir) / instance_type
            }
    
    @classmethod
    def available_configurations(cls, instance_type, system_folders):
        """Returns a list of configuration managers."""
        
        folders =  cls.instance_folders(instance_type, "", system_folders)
        
        # potential configuration files
        config_files = Path(folders["config"]).glob("*.yaml")
        
        configs = []
        failed = []
        for file_ in config_files:
            try:
                conf_manager = cls.INST_CONFIG_MANAGER.from_file(file_)
                if conf_manager.is_empty:
                    failed.append(file_)
                else:
                    configs.append(conf_manager)
            except Exception:                
                failed.append(file_)

        return configs, failed

class NodeContext(AppContext):
    """Node context on the host machine (used by the CLI). See 
    DockerNodeContext for the node instance mounts on the docker deamon"""
    
    INST_CONFIG_MANAGER = NodeConfigurationManager
    
    def __init__(self, instance_name, environment=constants.DEFAULT_NODE_ENVIRONMENT, system_folders=False):
        super().__init__("node", instance_name, environment=environment, 
            system_folders=system_folders)
    
    def get_database_uri(self, label="default"):
        return self.config["databases"][label]
    
    @property
    def databases(self):
        return self.config["databases"]

    @classmethod
    def from_external_config_file(cls, path, environment=constants.DEFAULT_NODE_ENVIRONMENT, system_folders=False):
        return super().from_external_config_file(
            path, "node", environment, system_folders
        )

    @classmethod
    def config_exists(cls, instance_name, environment=constants.DEFAULT_NODE_ENVIRONMENT, system_folders=False):
        return super().config_exists("node", 
            instance_name, environment=environment, system_folders=system_folders)
    
    @classmethod
    def available_configurations(cls, system_folders=constants.DEFAULT_NODE_SYSTEM_FOLDERS):
        return super().available_configurations("node", system_folders)

class DockerNodeContext(NodeContext):
    """Node context for the dockerized version of the node."""

    @staticmethod
    def instance_folders(instance_type, instance_name, system_folders):
        """Log, data and config folders are allways mounted mounted. The
        node manager should take care of this. """
        
        mnt = Path("/mnt")

        return {
            "log": mnt / "log",
            "data": mnt / "data",
            "config": mnt / "config"
        }


class ServerContext(AppContext):
    
    INST_CONFIG_MANAGER = ServerConfigurationManager

    def __init__(self, instance_name, 
        environment=constants.DEFAULT_SERVER_ENVIRONMENT, 
        system_folders=constants.DEFAULT_SERVER_SYSTEM_FOLDERS):
    
        super().__init__("server", instance_name, environment=environment, 
            system_folders=system_folders)

    def get_database_uri(self):
        uri = self.config['uri']
        URL = make_url(uri)

        if (URL.host is None) and (not os.path.isabs(URL.database)):
            # We're dealing with a relative path here.
            URL.database = str(self.data_dir / URL.database)
            uri = str(URL)

        return uri
    
    @classmethod
    def from_external_config_file(cls, path, 
        environment=constants.DEFAULT_SERVER_ENVIRONMENT, 
        system_folders=constants.DEFAULT_SERVER_SYSTEM_FOLDERS):

        return super().from_external_config_file(
            path, "server", environment, system_folders
        )

    @classmethod
    def config_exists(cls, instance_name, 
        environment=constants.DEFAULT_SERVER_ENVIRONMENT, 
        system_folders=constants.DEFAULT_SERVER_SYSTEM_FOLDERS):

        return super().config_exists("server", 
            instance_name, environment= environment, system_folders=system_folders)

    @classmethod
    def available_configurations(cls, 
        system_folders=constants.DEFAULT_SERVER_SYSTEM_FOLDERS):
        
        return super().available_configurations("server", system_folders)
        

class TestContext(AppContext):

    INST_CONFIG_MANAGER = TestingConfigurationManager
    LOGGING_ENABLED = False
    
    @classmethod
    def from_external_config_file(cls, path):
        return super().from_external_config_file(
            cls.test_config_location(), 
            "unittest", "application", True
        )

    @staticmethod
    def test_config_location():
        return ( constants.PACAKAGE_FOLDER / constants.APPNAME / \
            "_data" / "unittest_config.yaml")

    @staticmethod
    def test_data_location():
        return ( constants.PACAKAGE_FOLDER / constants.APPNAME / \
            "_data" )

def prepare_bytes_for_transport(bytes_):
    return base64.b64encode(bytes_).decode(constants.STRING_ENCODING)

def unpack_bytes_from_transport(bytes_string):
    return base64.b64decode(bytes_string.encode(constants.STRING_ENCODING))