import sys
import os

from vantage6 import node
from vantage6.node.context import DockerNodeContext, NodeContext


def start(name, environment, dev=False):
    """Start the node instance.

    If no name or config is specified the default.yaml configuation is used.
    In case the configuration file not exists, a questionaire is
    invoked to create one. Note that in this case it is not possible to
    specify specific environments for the configuration (e.g. test,
    prod, acc).
    """

    # create context
    # FIXME: this can be automatically detected ..,
    if dev == False:
        ctx = DockerNodeContext(name, environment)

    else:
        ctx = NodeContext(name, environment)

    # run the node application
    node.run(ctx)


# ------------------------------------------------------------------------------
# __main__
# ------------------------------------------------------------------------------
if __name__ == "__main__":

    # configuration name
    name = sys.argv[1]

    # environment in the config file (dev, test, acc, prod, application)
    environment = sys.argv[2]

    # Supplying dev-local runs a non dockerized version of the node.
    dev = False

    if len(sys.argv) > 3 and sys.argv[3] == "dev-local":
        dev = True

    # run script to start
    start(name, environment, dev)
