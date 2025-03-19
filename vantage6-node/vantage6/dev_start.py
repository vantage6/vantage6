import sys
import logging
from pathlib import Path
from vantage6.node.context import DockerNodeContext
from vantage6.node import run

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("vantage6.dev_start")


def run_function(config):

    if not config:
        log.critical("No config provided.")
        return

    name = Path(config).stem
    ctx = DockerNodeContext(name, True, config, logger_prefix=f"{name} | ")

    run(ctx)


if __name__ == "__main__":

    config_file = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not config_file:
        log.critical("No config file provided.")
        sys.exit(1)

    if not config_file.exists():
        log.critical("Config file does not exist: %s", config_file)
        sys.exit(1)

    log.info("Starting node with config: %s", config_file)
    run_function(config_file)
