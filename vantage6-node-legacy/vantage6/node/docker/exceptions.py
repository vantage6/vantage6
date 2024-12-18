"""
Below are some custom exception types that are raised when algorithms cannot
be executed successfully.
"""


#
#   Temporary failures
#
class TemporaryAlgorithmFail(Exception):
    """Algorithm failed to execute successfully, but potentially running it
    again would resolve the issue.
    """

    pass


class UnknownAlgorithmStartFail(TemporaryAlgorithmFail):
    """Algorithm failed to start due to an unknown reason."""

    pass


class AlgorithmContainerNotFound(TemporaryAlgorithmFail):
    """Algorithm container was lost."""

    pass


#
#   Permanent failures
#
class PermanentAlgorithmFail(Exception):
    """Algorithm failed to execute successfully and should not be attempted to
    be run again.
    """

    pass


class DataFrameNotFound(PermanentAlgorithmFail):
    """DataFrame was not found."""

    pass


class PermanentAlgorithmStartFail(PermanentAlgorithmFail):
    """Algorithm failed to start"""

    pass
