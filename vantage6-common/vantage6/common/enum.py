from enum import Enum


class StorePolicies(str, Enum):
    """
    Enum for the different types of policies of the algorithm store.
    """

    ALGORITHM_VIEW = "algorithm_view"
    ALLOWED_SERVERS = "allowed_servers"
    ALLOW_LOCALHOST = "allow_localhost"
    MIN_REVIEWERS = "min_reviewers"
    ASSIGN_REVIEW_OWN_ALGORITHM = "assign_review_own_algorithm"
    MIN_REVIEWING_ORGANIZATIONS = "min_reviewing_organizations"
    ALLOWED_REVIEWERS = "allowed_reviewers"
    ALLOWED_REVIEW_ASSIGNERS = "allowed_review_assigners"


class AlgorithmViewPolicies(str, Enum):
    """Enum for available algorithm view policies"""

    PUBLIC = "public"
    WHITELISTED = "whitelisted"
    ONLY_WITH_EXPLICIT_PERMISSION = "private"


class EnumBase(str, Enum):
    """Base class for all enums in this module"""

    @classmethod
    def list(cls) -> list[str]:
        """Return a list of all the enum values"""
        return [status.value.lower() for status in cls]


class AlgorithmStepType(EnumBase):
    """Enum to represent the local actions

    A container (= function) on a node can perform a single action. Depending on the
    action, different steps can be taken at the node. For example, the compute step
    does not require access to the original data source.
    """

    DATA_EXTRACTION = "data extraction"
    PREPROCESSING = "preprocessing"
    COMPUTE = "compute"
    POST_PROCESSING = "post processing"


class TaskDatabaseType(EnumBase):
    """Enum to represent the type of database used by a task"""

    SOURCE = "source"
    DATAFRAME = "dataframe"


class TaskStatus(EnumBase):
    """Enum to represent the status of a task"""

    # All runs have been completed
    COMPLETED = "completed"
    # At least one run has failed
    FAILED = "failed"
    # At least one run is not completed and no runs have failed
    WAITING = "awaiting"

    @classmethod
    def has_finished(cls, status) -> bool:
        """
        Check if task has finished

        Parameters
        ----------
        status: TaskStatus | str
            The status of the task

        Returns
        -------
        bool
            True if task has finished, False otherwise
        """
        return status in [cls.COMPLETED.value, cls.FAILED.value]


class RunStatus(EnumBase):
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

    # Unexpected output type from container
    UNEXPECTED_OUTPUT = "unexpected output"

    @classmethod
    def has_failed(cls, status) -> bool:
        """
        Check if task has failed to run to completion

        Parameters
        ----------
        status: RunStatus | str
            The status of the task

        Returns
        -------
        bool
            True if task has failed, False otherwise
        """
        return status in cls.failed_statuses()

    @classmethod
    def has_finished(cls, status) -> bool:
        """
        Check if task has finished or failed

        Parameters
        ----------
        status: RunStatus | str
            The status of the task

        Returns
        -------
        bool
            True if task has finished or failed, False otherwise
        """
        return status in cls.finished_statuses()

    @classmethod
    def failed_statuses(cls) -> list[str]:
        """Return a list of all the failed status values"""

        return [
            cls.FAILED.value,
            cls.CRASHED.value,
            cls.KILLED.value,
            cls.NOT_ALLOWED.value,
            cls.UNKNOWN_ERROR.value,
            cls.START_FAILED.value,
            cls.NO_DOCKER_IMAGE.value,
            cls.UNEXPECTED_OUTPUT.value,
            cls.DATAFRAME_NOT_FOUND.value,
        ]

    @classmethod
    def finished_statuses(cls) -> list[str]:
        """Return a list of all the finished status values"""

        return cls.failed_statuses() + [cls.COMPLETED.value]

    @classmethod
    def alive_statuses(cls) -> list[str]:
        """Return a list of all the status values where run is not completed"""

        return [
            cls.PENDING,
            cls.INITIALIZING.value,
            cls.ACTIVE.value,
        ]


class TaskStatusQueryOptions(EnumBase):

    OPEN = "open"
    WAITING = "waiting"
    FINISHED = "finished"
