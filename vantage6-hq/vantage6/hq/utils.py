import datetime as dt


def parse_datetime(
    date: str | dt.datetime | None = None, default: dt.datetime | None = None
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
            # DTZ007: %z is only appended above when present in the string; the
            # naive case is handled explicitly right below, so this is safe.
            parsed = dt.datetime.strptime(date, converter)  # noqa: DTZ007
            if parsed.tzinfo is None:
                # no timezone info was present in the string; assume UTC
                parsed = parsed.replace(tzinfo=dt.UTC)
            return parsed
        else:
            # convert datetime to UTC
            return date.astimezone(dt.UTC)
    return default
