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
