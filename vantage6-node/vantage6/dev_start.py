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

    class PrefixLogger(logging.Handler):
        def __init__(self, prefix):
            super().__init__()
            self.prefix = prefix

        def emit(self, record):
            log_entry = self.format(record)
            print(f"[{self.prefix}] {log_entry}")

    try:

        ctx = DockerNodeContext(name, True, config, logger_prefix=f"{name} | ")
        run(ctx)
    finally:
        pass
        # logger.removeHandler(handler)


if __name__ == "__main__":

    # Create a separate logger for each thread
    # logger = logging.getLogger()
    # logger.setLevel(logging.DEBUG)

    # # Clear existing handlers
    # if logger.hasHandlers():
    #     logger.handlers.clear()

    # handler = PrefixLogger(name)
    # formatter = logging.Formatter(
    #     "%(asctime)s - %(name)-14s - %(levelname)-8s - %(message)s"
    # )
    # handler.setFormatter(formatter)
    # logger.addHandler(handler)

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
