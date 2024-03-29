from enum import Enum


class SessionStatus(str, Enum):
    """Enum to represent the status of a session"""

    # Session creation has not yet started
    PENDING = "pending"
    # Session is executing the data extraction step(s)
    DATA_EXTRACTION = "data extraction"
    # Session is executing the preprocessing step(s)
    PREPROCESSING = "preprocessing"
    # Session is ready to be used by compute tasks
    READY = "ready"
    # Session creation has failed
    FAILED = "failed"

    @classmethod
    def list(cls):
        """Return a list of all the status values"""
        return [status.value.lower() for status in cls]
