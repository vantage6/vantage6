"""
TES relay mode for the Vantage6 node.

When enabled via node config (``tes_relay.enabled: true``), the node relays
Vantage6 tasks to a GA4GH TES-compatible endpoint (e.g. the DARE Submission
Layer), polls for completion and returns results to the Vantage6 server.
"""

from vantage6.node.tes_relay.manager import TesRelayManager

__all__ = ["TesRelayManager"]
