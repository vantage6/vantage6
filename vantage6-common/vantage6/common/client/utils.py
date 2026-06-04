import uuid


def is_uuid(value: str) -> bool:
    """
    Check if value is a valid UUID.

     Parameters
    ----------
    value : str
        The value to check.

     Returns
    -------
    `True` if value is a valid UUID, otherwise `False`.
    """
    try:
        uuid_obj = uuid.UUID(value)
    except (ValueError, TypeError, AttributeError):
        return False
    return str(uuid_obj) == value
