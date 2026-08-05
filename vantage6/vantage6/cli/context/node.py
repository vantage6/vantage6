# NodeContext now lives in vantage6-common so the node can start without importing
# the CLI package. We re-export it here for code that still uses the old path.
from vantage6.common.node_context import NodeContext

__all__ = ["NodeContext"]
