# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

import sys
import os, os.path
import pprint

import logging
import logging.handlers

import yaml

from jsdict import JSDict


def loadConfig(filename):
    with open(filename) as fp:
        config = yaml.load(fp)
        config = JSDict(config)

    return config


def setupLogging(config):
    """Setup a basic logging mechanism."""
    level = config.logging.level
    
    if level == 'NONE':
        return
    
    level = getattr(logging, level.upper())
    
    filename = config.logging["file"]
    format = config.logging["format"]
    bytes = config.logging["max_size"]
    backup_count = config.logging["backup_count"]
    datefmt = config.logging.get("datefmt", "")

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
    if config.logging["use_console"]:
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
      


# ------------------------------------------------------------------------------
def init(application, config_file='config.yaml'):
  """Set the CWD, load the config file and setup logging."""
  # Read the command line parameters and change directory to the application
  # root. 
  app = sys.argv[0]
  dirname = os.path.dirname(app)
  
  if 'ipython' not in app:
    chdir(dirname)
  
  config = loadConfig(config_file)
  setupLogging(config)
  
  log = logging.getLogger(__name__)
  
  log.info("#" * 80)
  log.info('#{:^78}#'.format(application))
  log.info("#" * 80)
  log.info("Started application '%s'" % application)
  log.info("Current working directory is '%s'" % os.getcwd())
  log.info("Succesfully loaded configuration from '%s'" % config_file)
  
  return config

    