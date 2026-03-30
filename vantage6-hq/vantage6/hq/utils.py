import datetime as dt


def parse_datetime(
    date: str | dt.datetime = None, default: dt.datetime = None
) -> dt.datetime:
    """
    Utility function to parse a datetime string.

    Parameters
    ----------
    date : str | datetime.datetime, optional
        Datetime string
    default : datetime.datetime, optional
        Default datetime to return if `dt` is None

    Returns
    -------
    datetime.datetime
        Datetime object
    """
    if date:
        if isinstance(date, str):
            converter = "%Y-%m-%dT%H:%M:%S.%f"
            if date.endswith("+00:00"):
                converter += "%z"  # parse timezone
            return dt.datetime.strptime(date, converter)
        else:
            # convert datetime to UTC
            return date.astimezone(dt.timezone.utc)
    return default
