import sys
import threading
import logging
from pathlib import Path
from vantage6.node.context import DockerNodeContext
from vantage6.node import run


def run_function(config):
    if not config:
        print("No config provided")
        return

    name = Path(config).stem
    print("BYEEEE")
    # DockerNodeContext.LOGGING_ENABLED = True
    ctx = DockerNodeContext(name, True, config, logger_prefix=f"{name} | ")

    run(ctx)


if __name__ == "__main__":

    config_folder = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    configs = config_folder.glob("*.yaml")

    configs = [str(config_path) for config_path in list(configs)]
    threads = []
    for config in configs:
        print(f"Starting node with config: {config}")
        thread = threading.Thread(target=run_function, args=(config,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()
