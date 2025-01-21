import sys

from pathlib import Path

from vantage6.node.context import DockerNodeContext
from vantage6.node import run

config = sys.argv[1] if len(sys.argv) > 1 else None
if not config:

    exit(1)
name = Path(config).stem
ctx = DockerNodeContext(name, True, config)
run(ctx)
