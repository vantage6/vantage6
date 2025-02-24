import sys
import threading
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

    config_folder = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not config_folder:
        log.critical("No config folder provided.")
        sys.exit(1)

    configs = config_folder.glob("*.yaml")
    configs = [str(config_path) for config_path in list(configs)]
    threads = []

    for config in configs:
        log.info(f"Starting node with config: {config}")
        thread = threading.Thread(target=run_function, args=(config,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
