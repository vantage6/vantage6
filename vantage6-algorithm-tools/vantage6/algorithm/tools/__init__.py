"""Algorithm tools support the development of algorithms for the vantage6 platform."""

from vantage6.common.enum import StrEnumBase

# make sure the version is available
from vantage6.algorithm.client import __version__  # noqa: F401


class DecoratorStepType(StrEnumBase):
    """Type of the decorator step"""

    DATA_EXTRACTION = "data_extraction"
    PREPROCESSING = "preprocessing"
    FEDERATED = "federated"
    CENTRAL = "central"
