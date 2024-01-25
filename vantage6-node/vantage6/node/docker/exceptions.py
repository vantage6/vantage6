"""
Below are some custom exception types that are raised when algorithms cannot
be executed successfully.
"""


class UnknownAlgorithmStartFail(Exception):
    """Algorithm failed to start due to an unknown reason. Potentially running
    it again would resolve the issue.
    """

    pass


class PermanentAlgorithmStartFail(Exception):
    """Algorithm failed to start and should not be attempted to be started
    again.
    """

    pass


class AlgorithmContainerNotFound(Exception):
    """Algorithm container was lost. Potentially running it again would
    resolve the issue.
    """

    pass
