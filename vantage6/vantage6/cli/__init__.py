"""Command line interface for the vantage6 infrastructure."""

import importlib.metadata

# note that here we cannot use __package__ because __package__ resolves to vantage6.cli
# whereas the PyPi package is called vantage6
__version__ = importlib.metadata.version("vantage6")
