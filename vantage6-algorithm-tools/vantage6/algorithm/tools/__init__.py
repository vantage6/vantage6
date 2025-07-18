"""Algorithm tools support the development of algorithms for the vantage6 platform."""

from enum import Enum

# make sure the version is available
from vantage6.algorithm.client._version import __version__  # noqa: F401


class DecoratorStepType(Enum):
    """Type of the decorator step"""

    DATA_EXTRACTION = "data_extraction"
    PREPROCESSING = "preprocessing"
    FEDERATED = "federated"
    CENTRAL = "central"
