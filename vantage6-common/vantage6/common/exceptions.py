class AuthenticationException(Exception):
    """Exception to indicate authentication has failed"""


class EncryptionMismatchError(Exception):
    """Exception to indicate that the node's encryption setting does not match the
    encryption setting of the collaboration it belongs to."""


class AlgorithmRetrievalError(Exception):
    """Exception to indicate that an algorithm could not be retrieved from an
    algorithm store."""


class SuperUserAlreadyExistsError(Exception):
    """Exception to indicate that the super user already exists when it was
    expected not to (e.g. on first-time HQ setup)."""
