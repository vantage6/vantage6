# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys
import os, os.path
import pprint

import pytaskmanager.util.Colorer
import logging
import logging.handlers

import appdirs
import yaml
from sqlalchemy.engine.url import make_url

CONFIG_FILE = 'config.yaml'

# ------------------------------------------------------------------------------
class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]




# ------------------------------------------------------------------------------
class AppContext(metaclass=Singleton):

    def __init__(self, application, instance_type, instance_name='', version=None):
        """Initialize a new instance.

            instance_type: {'server', 'node', 'unittest', 'fixtures'}
            instance_name: only relevant for nodes/servers
        """
        instance_types = ('server', 'node', 'unittest')
        msg = "instance_type should be one of {}".format(instance_types)
        assert instance_type in instance_types, msg

        self.application = application
        self.environment = None
        self.instance_type = instance_type
        self.instance_name = instance_name
        self.version = version
        self.config = None

        d = appdirs.AppDirs(application, '', version=version)
        self.dirs = {
            'data': d.user_data_dir,
            'log': d.user_log_dir,
            'config': d.user_config_dir,
        }

    @staticmethod
    def package_directory():
        here = os.path.abspath(os.path.dirname(__file__))
        return os.path.normpath(os.path.join(here, '../'))

    @classmethod
    def package_data_dir(cls):

        return os.path.join(cls.package_directory(), '_data')

    @property
    def data_dir(self):
        return self.get_file_location('data', '')

    @property
    def log_dir(self):
        return self.get_file_location('log', '')

    @property
    def config_dir(self):
        return self.get_file_location('config', '')

    @property
    def config_file(self):
        if self.instance_type == 'unittest':
            filename = 'unittest_config.yaml'
        else:
            filename = self.instance_name + '.yaml'

        return os.path.join(self.config_dir, filename)

    @property
    def config_available(self):
        """Return true if a config file is available."""
        return os.path.exists(self.config_file)

    def init(self, config_file, environment=None):
        """Load the configuration from disk and setup logging."""
        self.environment = environment if environment else 'test'
        print(f"argument enviroment={environment}")

        # Load configuration
        config = self.load_config(config_file)

        # FIXME: this is a hack!
        # TODO we changed the config file, app is no longer used as 
        # all is enviroment specific
        cfg_app = config['application']
        cfg_env = config['application']['environments'][self.environment]
        # cfg_env = config.get('environments', {}).get(environment)

        self.config = {
            'app': cfg_app,
            'env': cfg_env,
        }

        if environment is None:
            # Use 'application' rather than the configuration in a specific environment
            # Override default locations based on OS defaults if defined in 
            # configuration file
            if self.config.get('data_dir'):
                self.dirs['data_dir'] = cfg_app.get('data_dir')

            if self.config.get('log_dir'):
                self.dirs['log_dir'] = cfg_app.get('log_dir')
        else:
            # Apparently we're running a server (why else use an environment)
            # Override default locations based on OS defaults if defined in 
            # configuration file
            if self.config.get('data_dir'):
                self.dirs['data_dir'] = cfg_env.get('data_dir')

            if self.config.get('log_dir'):
                self.dirs['log_dir'] = cfg_env.get('log_dir')

        # Setup logging
        log_file = self.setup_logging()
        
        # Create a logger
        module_name = __name__.split('.')[-1]
        log = logging.getLogger(module_name)
        
        # Make some history
        log.info("#" * 80)
        log.info('#{:^78}#'.format(self.application))
        log.info("#" * 80)
        log.info("Started application '%s' with environment '%s'" % (self.application, environment))
        log.info("Current working directory is '%s'" % os.getcwd())
        log.info("Succesfully loaded configuration from '%s'" % config_file)
        log.info("Logging to '%s'" % log_file)

        # Return the configuration for the current application.            
        return self.config

    def load_config(self, config_file):
        """Load configuration from disk."""
        try:
            config = yaml.load( open(config_file) )
        except:
            msg = "Could not load configuration from '{}'"
            print(msg.format(config_file))
            raise
        
        return config

    def setup_logging(self):
        """Setup a basic logging mechanism."""
        if self.environment is None:
            print(f"no environment found")
            config = self.config['app']
        else:
            config = self.config['env']
            print(f"enviroment found {self.environment}")
        print(self.config)

        if ('logging' not in config) or (config["logging"]["level"].upper() == 'NONE'):
            return

        level = config["logging"]["level"]        
        level = getattr(logging, level.upper())
        
        filename = config["logging"]["file"]
        filename = self.get_file_location('log', filename)

        format = config["logging"]["format"]
        bytes = config["logging"]["max_size"]
        backup_count = config["logging"]["backup_count"]
        datefmt = config["logging"].get("datefmt", "")

        # print("trying to create directory '{}'".format(filename))
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Create the root logger
        logger = logging.getLogger()
        logger.setLevel(level)
        
        # Create RotatingFileHandler
        rfh = logging.handlers.RotatingFileHandler(filename, 
                                                   maxBytes=1024*bytes, 
                                                   backupCount=backup_count)
        rfh.setLevel(level)
        rfh.setFormatter(logging.Formatter(format, datefmt))
        logger.addHandler(rfh)
        
        # Check what to do with the console output ...
        if config["logging"]["use_console"]:
            ch = logging.StreamHandler(sys.stdout)
            ch.setLevel(level)
            ch.setFormatter(logging.Formatter(format, datefmt))
            logger.addHandler(ch)
            
            from pytaskmanager import util
            util.using_console_for_logging = True
          
        
        # Finally, capture all warnings using the logging mechanism.
        logging.captureWarnings(True)

        return filename

    def get_file_location(self, filetype, filename):
        """
        filetype: ('config', log', 'data')
        """
        if os.path.isabs(filename):
            return filename

        if self.instance_type in ('unittest', ):
            filename = os.path.join(self.dirs[filetype], filename)

        elif self.instance_type in ('server', 'node'):
            elements = [
                self.dirs[filetype], 
                self.instance_type
            ]

            if filetype == 'data':
                elements.append(self.instance_name)
            
            elements.append(filename)
            filename = os.path.join(*elements)

        return filename

    def get_database_location(self):
        uri = self.config['env']['uri']
        URL = make_url(uri)

        if (URL.host is None) and (not os.path.isabs(URL.database)):
            # We're dealing with a relative path here.
            URL.database = self.get_file_location('data', URL.database)
            uri = str(URL)

        return uri


class ServerContext(AppContext):
    def __init__(self, application, instance_name='', version=None):
        """Initialize a new instance.

            instance_name: only relevant for nodes/servers
        """
        super().__init__(application, 'server', instance_name, version=version)

        d = appdirs.AppDirs(application, version=version)
        self.dirs = {
            'data': d.site_data_dir,
            'log': d.site_data_dir,
            'config': d.site_config_dir,
        }


    def get_file_location(self, filetype, filename):
        """
        filetype: ('config', log', 'data')
        """
        if os.path.isabs(filename):
            return filename

        elements = [
            self.dirs[filetype], 
            self.instance_type
        ]

        if filetype == 'data':
            elements.append(self.instance_name)
        
        elements.append(filename)
        filename = os.path.join(*elements)

        return filename



class NodeContext(AppContext):
    pass


class FixturesContext(AppContext):
    pass


class TestContext(AppContext):
    def __init__(self):
        super().__init__('unittest', 'unittest')

    def get_file_location(self, filetype, filename):
        """
        filetype: ('config', log', 'data')
        """
        if os.path.isabs(filename):
            return filename

        if filetype == 'config':
            return os.path.join(self.package_data_dir(), filename)

        return super().get_file_location(filetype, filename)

    
