class AlgorithmError(Exception):
    """Generic exception raised when an algorithm fails."""


# ---------------- Privacy exceptions ----------------
class PrivacyViolation(AlgorithmError):
    """Generic exception raised for data privacy concerns."""


class PrivacyThresholdViolation(PrivacyViolation):
    """
    Raised when privacy threshold is violated.

    Example usage:
    - The number of rows in the data is too low.
    - Returning the results of the algorithm would violate privacy.
    """


# ---------------- Data exceptions ----------------


class DataError(AlgorithmError):
    """Generic error raised with data handling."""


class DataReadError(DataError):
    """Raised when data reading fails.

    Example usage:
    - File not found.
    - File is not in the right format.
    - File is not readable.
    - File is empty.
    """


class DataTypeError(DataError):
    """Raised when data type is invalid.

    Example usage:
    - String column is selected by user for numeric operation.
    """


# ---------------- Runtime exceptions ----------------
class AlgorithmRuntimeError(AlgorithmError):
    """Generic error raised when an algorithm fails at runtime."""


class AlgorithmExecutionError(AlgorithmRuntimeError):
    """Raised when algorithm function fails.

    Use when the algorithm function raises an exception.
    """


class MaxIterationsReached(AlgorithmRuntimeError):
    """Raised when the maximum number of iterations is reached."""


class ConvergenceError(AlgorithmRuntimeError):
    """Raised when the algorithm fails to converge."""


# ---------------- Client exceptions ----------------


class ClientError(AlgorithmError):
    """Generic error raised when call to the algorithm client fails."""


# the most common client errors are defined separately for clarity
class SubtakCreationError(ClientError):
    """Raised when subtask creation fails."""


class CollectOrganizationError(ClientError):
    """Raised when organization collection fails."""


class CollectResultsError(ClientError):
    """Raised when result collection fails."""


# ---------------- Input exceptions ----------------


class InputError(AlgorithmError):
    """Generic error raised with algorithm input handling.
    Example usage:
    - User input is invalid.
    - Subtask fails due to invalid input received from the parent task.
    """


class UserInputError(InputError):
    """Raised when user input is invalid.

    Example usage:
    - User input is not in the expected format.
    """


class DeserializationError(InputError):
    """Raised when result deserialization fails."""


# TODO v5+ remove this alias, which is there for backwards compatibility
DeserializationException = DeserializationError


class EnvironmentVariableError(InputError):
    """
    Error raised when environment variable handling fails.

    Example usage:
    - Environment variables have conflicting values
    - Environment variable has an invalid value (e.g. not a number where number is
    expected)
    """


class EnvironmentVariableNotFoundError(EnvironmentVariableError):
    """Raised when environment variable is not found."""


# ---------------- Initialization exceptions ----------------


class AlgorithmInitializationError(AlgorithmError):
    """Generic error raised when algorithm initialization fails."""


class AlgorithmModuleNotFoundError(AlgorithmInitializationError):
    """
    Raised when the algorithm module is not found.

    Note that if this error is raised, the algorithm image is not built correctly.
    """


class MethodNotFoundError(AlgorithmInitializationError):
    """
    Raised when the algorithm method is not found.

    This error may be raised if the user calls a non-existing method, or if the
    algorithm image is not built correctly.
    """


# ---------------- Exceptions for conflicts with node settings ----------------


class NodePermissionException(AlgorithmError):
    """
    Generic error raised when the node does not allow the computation of a certain
    request.

    Example usage:
    - The node does not allow the computation to be executed on a certain data column.
    """


# ---------------- Session exceptions ----------------


class SessionError(AlgorithmError):
    """
    Generic error raised when a step of the session fails.

    Example usage:
    - The function requested to be executed to build the session is not started using
      the correction action (data extraction, preprocessing, etc.)
    """
