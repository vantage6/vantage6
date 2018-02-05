# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys
import os, os.path
import pprint

import logging
import logging.handlers

import yaml

import db


def setupDatabase(environment, config, drop_all=None):
  log = logging.getLogger(__name__)
  log.info("Using SQLAlchemy version {}".format(db.sqlalchemy.__version__))
  cfg = config['environments'][environment]
  uri = cfg['uri']
  
  if drop_all is None:
      drop_all = False
  
      # drop_all can only be configured on non-production environments
      if not environment.startswith('prod'):
          drop_all = cfg['drop_all']

  db.init(uri, drop_all)



def setupConfig(filename):
  config = yaml.load( open(filename) )
  return config


def setupLogging(config):
  """Setup a basic logging mechanism.
  
  @type  config: dict
  @param config: dict instance with the following keys in section 
    C{logging}: C{loglevel}, C{logfile}, C{format}, C{max_size}, C{backup_count}
    and C{use_console}.  
  """
  level = config["logging"]["level"]
  
  if level == 'NONE':
    return
  
  level = getattr(logging, level.upper())
  
  filename = config["logging"]["file"]
  format = config["logging"]["format"]
  bytes = config["logging"]["max_size"]
  backup_count = config["logging"]["backup_count"]
  datefmt = config["logging"].get("datefmt", "")

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
    
    import util
    util.using_console_for_logging = True
    
  
  # Finally, capture all warnings using the logging mechanism.
  logging.captureWarnings(True)


def chdir(dirname=None):
    if not dirname:
        app = sys.argv[0]
        dirname = os.path.dirname(app)
    
    try:
        # This may fail if dirname == ''
        os.chdir(dirname)
    except:
        print("Could not change directory to: '%s'" % dirname)
      

class JSONStructure(object):
    """JavaScript-like (read only) access to JSON data."""
    def __init__(self, json_obj):
        self._json_obj = json_obj
    
    def __getattr__(self, key):
        value = self._json_obj[key]
        
        if type(value) in [list, dict]:
            return JSONStructure(value)
        
        return value
    
    def __contains__(self, item):
        return self._json_obj.__contains__(item)
    
    def __getitem__(self, idx):
        return self.__getattr__(idx)
    
    def __setitem__(self, idx, value):
        self._json_obj[idx] = value
        
    def append(self, item):
        self._json_obj.append(item)
    
    def __repr__(self):
        return pprint.pformat(self._json_obj)
    
    

# ------------------------------------------------------------------------------
def init(application, environment='test', config_file='config.yaml', setup_database=True, drop_all=None):
  """Set the CWD, load the config file and setup logging."""
  # Read the command line parameters and change directory to the application
  # root. 
  app = sys.argv[0]
  dirname = os.path.dirname(app)
  
  if 'ipython' not in app:
    chdir(dirname)
  
  config = setupConfig(config_file)
  setupLogging(config['applications'][application])
  
  log = logging.getLogger(__name__)
  
  log.info("#" * 80)
  log.info('#{:^78}#'.format(application))
  log.info("#" * 80)
  log.info("Started application '%s' with environment '%s'" % (application, environment))
  log.info("Current working directory is '%s'" % os.getcwd())
  log.info("Succesfully loaded configuration from '%s'" % config_file)
  
  if setup_database:
    log.info("Configuring database ...")
    setupDatabase(environment, config, drop_all)
  
  cfg = {
      'app': config['applications'][application],
      'env': config['environments'][environment],
  }
  
  return cfg

    