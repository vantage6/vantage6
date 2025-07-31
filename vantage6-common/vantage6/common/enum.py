from enum import Enum, StrEnum

# Note: List is used instead of regular list, because StrEnumBase already contains list()
from typing import List


class EnumBase(Enum):
    """Base class for all enums"""

    @classmethod
    def list(cls) -> List[str]:
        """Return a list of all the enum values"""
        return [status.value for status in cls]

    @classmethod
    def names(cls) -> List[str]:
        """Return a list of all the enum names"""
        return [status.name.lower() for status in cls]

    @classmethod
    def items(cls) -> List[tuple[str, str]]:
        """Return a list of (name, value) tuples for all enum members"""
        return [(status.name.lower(), status.value) for status in cls]


class StrEnumBase(StrEnum, EnumBase):
    """Base class for all enums"""


class StorePolicies(StrEnumBase):
    """
    Enum for the different types of policies of the algorithm store.
    """

    ALGORITHM_VIEW = "algorithm_view"
    MIN_REVIEWERS = "min_reviewers"
    ASSIGN_REVIEW_OWN_ALGORITHM = "assign_review_own_algorithm"
    MIN_REVIEWING_ORGANIZATIONS = "min_reviewing_organizations"
    ALLOWED_REVIEWERS = "allowed_reviewers"
    ALLOWED_REVIEW_ASSIGNERS = "allowed_review_assigners"


class AlgorithmViewPolicies(StrEnumBase):
    """Enum for available algorithm view policies"""

    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    ONLY_WITH_EXPLICIT_PERMISSION = "private"


class AlgorithmStepType(StrEnumBase):
    """Enum to represent the local actions

    A container (= function) on a node can perform a single action. Depending on the
    action, different steps can be taken at the node. For example, the compute step
    does not require access to the original data source.
    """

    DATA_EXTRACTION = "data_extraction"
    PREPROCESSING = "preprocessing"
    FEDERATED_COMPUTE = "federated_compute"
    CENTRAL_COMPUTE = "central_compute"
    POST_PROCESSING = "postprocessing"

    @classmethod
    def is_compute(cls, step_type: str) -> bool:
        """Check if the step type is a compute step"""
        return step_type in [cls.FEDERATED_COMPUTE, cls.CENTRAL_COMPUTE]


class TaskDatabaseType(StrEnumBase):
    """Enum to represent the type of database used by a task"""

    SOURCE = "source"
    DATAFRAME = "dataframe"


class DatabaseType(StrEnumBase):
    """Enum to represent the type of database"""

    CSV = "csv"
    EXCEL = "excel"
    SPARQL = "sparql"
    PARQUET = "parquet"
    SQL = "sql"
    OMOP = "omop"
    OTHER = "other"
    FOLDER = "folder"

    def is_file_based(self) -> bool:
        """Check if the database type is file-based"""
        return self in [
            self.CSV,
            self.EXCEL,
            self.PARQUET,
            self.FOLDER,
        ]


class TaskStatus(StrEnumBase):
    """Enum to represent the status of a task"""

    # All runs have been completed
    COMPLETED = "completed"
    # At least one run has failed
    FAILED = "failed"
    # At least one run is not completed and no runs have failed
    WAITING = "awaiting"

    @classmethod
    def has_finished(cls, status: str) -> bool:
        """
        Check if task has finished

        Parameters
        ----------
        status: str
            The status of the task

        Returns
        -------
        bool
            True if task has finished, False otherwise
        """
        return status in [cls.COMPLETED, cls.FAILED]


class RunStatus(StrEnumBase):
    """Enum to represent the status of a run"""

    # Task has not yet been started (usually, node is offline)
    PENDING = "pending"
    # Task is being started
    INITIALIZING = "initializing"
    # Container started without exceptions
    ACTIVE = "active"
    # Container exited and had zero exit code
    COMPLETED = "completed"

    # Generic fail status
    FAILED = "failed"
    # Failed to start the container on the first attempt
    START_FAILED = "start failed"
    # Could not start because docker image didn't exist
    NO_DOCKER_IMAGE = "non-existing Docker image"
    # Container had a non zero exit code
    CRASHED = "crashed"
    # Container was killed by user
    KILLED = "killed by user"
    # Task was not allowed by node policies
    NOT_ALLOWED = "not allowed"
    # Task failed without exit code
    UNKNOWN_ERROR = "unknown error"
    # Datafrome was not found
    DATAFRAME_NOT_FOUND = "dataframe not found"
    # Task was not executed because a task that it depended on failed
    DEPENDED_ON_FAILED_TASK = "depended on failed task"

    # Unexpected output type from container
    UNEXPECTED_OUTPUT = "unexpected output"

    @classmethod
    def has_failed(cls, status: str) -> bool:
        """
        Check if run has failed to complete

        Parameters
        ----------
        status: str
            The status of the task

        Returns
        -------
        bool
            True if run has failed, False otherwise
        """
        return status in cls.failed_statuses()

    @classmethod
    def has_finished(cls, status: str) -> bool:
        """
        Check if run has finished or failed

        Parameters
        ----------
        status: str
            The status of the run

        Returns
        -------
        bool
            True if run has finished or failed, False otherwise
        """
        return status in cls.finished_statuses()

    @classmethod
    def failed_statuses(cls) -> list[str]:
        """Return a list of all the failed status values"""

        return [
            cls.FAILED,
            cls.CRASHED,
            cls.KILLED,
            cls.NOT_ALLOWED,
            cls.UNKNOWN_ERROR,
            cls.START_FAILED,
            cls.NO_DOCKER_IMAGE,
            cls.UNEXPECTED_OUTPUT,
            cls.DATAFRAME_NOT_FOUND,
            cls.DEPENDED_ON_FAILED_TASK,
        ]

    @classmethod
    def finished_statuses(cls) -> list[str]:
        """Return a list of all the finished status values"""

        return cls.failed_statuses() + [cls.COMPLETED]

    @classmethod
    def alive_statuses(cls) -> list[str]:
        """Return a list of all the status values where run is not completed"""

        return [
            cls.PENDING,
            cls.INITIALIZING,
            cls.ACTIVE,
        ]


class TaskStatusQueryOptions(StrEnumBase):
    """Enum for different options for querying task statuses"""

    OPEN = "open"
    WAITING = "waiting"
    FINISHED = "finished"


class AlgorithmArgumentType(StrEnumBase):
    """Enum for argument types"""

    COLUMN = "column"
    COLUMNS = "column_list"
    STRING = "string"
    STRINGS = "string_list"
    INTEGER = "integer"
    INTEGERS = "integer_list"
    FLOAT = "float"
    FLOATS = "float_list"
    BOOLEAN = "boolean"
    JSON = "json"
    ORGANIZATION = "organization"
    ORGANIZATIONS = "organization_list"
