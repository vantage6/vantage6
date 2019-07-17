import sys

from joey import util, node

def start(name, environment):
    """Start the node instance.
    
    If no name or config is specified the default.yaml configuation is used. 
    In case the configuration file not exists, a questionaire is
    invoked to create one. Note that in this case it is not possible to
    specify specific environments for the configuration (e.g. test, 
    prod, acc). 
    """
    
    # create context
    ctx = util.DockerNodeContext(name, environment)

    # run the node application
    node.run(ctx)

def start_development(name, environment):
    ctx = util.NodeContext(name, environment)
    node.run(ctx)

if __name__ == "__main__":

    # configuration name
    name = sys.argv[1]
    
    # environment in the config file (dev, test, acc, prod, application)
    environment = sys.argv[2]

    # development or not
    if len(sys.argv) > 3:
        start_development(name, environment)
    else:
        # run script to start
        start(name, environment)