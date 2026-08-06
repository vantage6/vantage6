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


class UnknownAlgorithmStartFail(TemporaryAlgorithmFail):
    """Algorithm failed to start due to an unknown reason."""


class AlgorithmContainerNotFound(TemporaryAlgorithmFail):
    """Algorithm container was lost."""


#
#   Permanent failures
#
class PermanentAlgorithmFail(Exception):
    """Algorithm failed to execute successfully and should not be attempted to
    be run again.
    """


class DataFrameNotFound(PermanentAlgorithmFail):
    """DataFrame was not found."""


class PermanentAlgorithmStartFail(PermanentAlgorithmFail):
    """Algorithm failed to start"""
