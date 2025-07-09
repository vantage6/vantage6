"""Algorithm tools support the development of algorithms for the vantage6 platform."""

from enum import Enum

# make sure the version is available
from vantage6.algorithm.client._version import __version__  # noqa: F401


class DecoratorType(Enum):
    """Type of the decorator"""

    DATAFRAME = "dataframe"
    DATA_EXTRACTION = "data_extraction"
    PREPROCESSING = "preprocessing"
    FEDERATED = "federated"
    CENTRAL = "central"
    ALGORITHM_CLIENT = "algorithm_client"
    METADATA = "metadata"
    SOURCE_DATABASE = "source_database"
