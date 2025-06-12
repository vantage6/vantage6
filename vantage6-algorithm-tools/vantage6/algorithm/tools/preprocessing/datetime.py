"""
This module provides a set of utility functions for converting and manipulating
datetime and timedelta columns in pandas DataFrames. It includes capabilities
for converting strings to datetime, adding fixed or variable timedeltas, and
calculating ages from birthdate columns.
"""

from datetime import date

import pandas as pd


def to_datetime(
    df: pd.DataFrame,
    column: str,
    fmt: str | None = None,
    errors: str = "raise",
    output_column: str | None = None,
) -> pd.DataFrame:
    """
    Convert a string column to a datetime column in a new DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    column : str
        The name of the column to convert.
    fmt : str | None, optional
        String to use as date format. See the following link for more
        information: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
    errors : str, default 'raise'
        Errors handling if a string cannot be converted:
        * If 'raise', then invalid parsing will raise an exception.
        * If 'coerce', then invalid parsing will be set as NaT.
        * If 'ignore', then invalid parsing will return the input.
    output_column : str | None, optional
        Name for the output column of converted dates. If not specified, the input
        column will be overwritten.

    Returns
    -------
    pd.DataFrame
        DataFrame with the converted column.

    Examples
    --------
    >>> df = pd.DataFrame({"date_str": ["2021-01-01", "2021-02-01", "2021-03-01"]})
    >>> to_datetime(df, "date_str")
        date_str
    0 2021-01-01
    1 2021-02-01
    2 2021-03-01

    >>> df = pd.DataFrame({"date_str": ["Jan 01, 2021", "Feb 01, 2021", "Mar 01, 2021"]})
    >>> to_datetime(df, "date_str", fmt='%b %d, %Y')
        date_str
    0 2021-01-01
    1 2021-02-01
    2 2021-03-01

    >>> df = pd.DataFrame({"date_str": ["01-2021-01", "01-2021-02", "Invalid"]})
    >>> to_datetime(df, "date_str", fmt='%d-%Y-%m', errors='coerce')
        date_str
    0 2021-01-01
    1 2021-02-01
    2        NaT
    """

    new_df = df.copy()
    conversion_column = output_column if output_column else column
    new_df[conversion_column] = pd.to_datetime(
        new_df[column], format=fmt, errors=errors
    )

    return new_df


def to_timedelta(
    df: pd.DataFrame,
    input_column: str | None = None,
    duration: str | int | None = None,
    unit: str = "days",
    output_column: str | None = None,
    errors: str = "raise",
) -> pd.DataFrame:
    """
    Convert a string column or apply a fixed duration to a new timedelta column
    in a new DataFrame.

    For more information see:
    https://pandas.pydata.org/docs/reference/api/pandas.Timedelta.html

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    input_column : str | None, optional
        The name of the column to convert.
    duration : str | int | None, optional
        A fixed duration to apply to all rows. Could be either a string like
        '1 days' or an integer.
    unit : str, default 'days'
        The unit for the fixed duration, applicable when `duration` is an
        integer.

        Possible values:
        * 'W', 'D', 'T', 'S', 'L', 'U', or 'N'
        * 'days' or 'day'
        * 'hours', 'hour', 'hr', or 'h'
    output_column : str | None, optional
        The name of the output column. Required if using the `duration`
        parameter.
    errors : str, default 'raise'
        Error handling if a string cannot be converted:
        * If 'raise', then invalid parsing will raise an exception.
        * If 'coerce', then invalid parsing will be set as NaT.
        * If 'ignore', then invalid parsing will return the input.

    Returns
    -------
    pd.DataFrame
        DataFrame with the new converted or created column, retaining the
        original column.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"time_str": ["1 days", "2 days", "3 days"]})
    >>> to_timedelta(df, input_column="time_str", output_column="new_column")
      time_str new_column
    0   1 days     1 days
    1   2 days     2 days
    2   3 days     3 days

    >>> to_timedelta(df, duration=4, unit='W', output_column="fixed_timedelta")
      time_str fixed_timedelta
    0   1 days         28 days
    1   2 days         28 days
    2   3 days         28 days

    >>> to_timedelta(df, duration=48, unit='hours', output_column="duration")
      time_str duration
    0   1 days   2 days
    1   2 days   2 days
    2   3 days   2 days
    """
    if input_column is not None and duration is not None:
        raise ValueError(
            "Either `input_column` or `duration` must be specified, not both."
        )

    new_df = df.copy()

    if input_column is not None:
        if output_column is None:
            raise ValueError(
                "The `output_column` must be specified when using `column`."
            )
        if pd.api.types.is_numeric_dtype(new_df[input_column]):
            new_df[output_column] = pd.to_timedelta(
                new_df[input_column].astype(str) + " " + unit, errors=errors
            )

        else:
            new_df[output_column] = pd.to_timedelta(
                new_df[input_column], errors=errors
            )
    elif duration is not None:
        if output_column is None:
            raise ValueError(
                "The `output_column` must be specified when using `duration`."
            )
        if isinstance(duration, int):
            duration = f"{duration} {unit}"
        new_df[output_column] = pd.to_timedelta(duration, errors=errors)

    if input_column is None and duration is None:
        raise ValueError("Either `column` or `duration` must be specified.")

    return new_df


def timedelta(
    df: pd.DataFrame,
    column: str,
    output_column: str = "timedelta",
    to_date: pd.Timestamp | None = None,
    to_date_column: str | None = None,
    fmt: str | None = None,
) -> pd.DataFrame:
    """
    Convert a datetime column to a timedelta column in days in a new DataFrame,
    where the result is the number of days since the date in the column to the
    reference date or reference column, which defaults to today.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    column : str
        The name of the datetime column to convert to a timedelta.
    output_column : str
        Output column name.
    to_date : pd.Timestamp | None, optional
        The date to which the timedelta is calculated. Defaults to today if not
        provided.
    to_date_column : str | None, optional
        A column containing dates to which the timedelta is calculated for each
        row. If not provided, `to_date` is used for all rows.
    fmt : str | None, optional
        The format to use for parsing date strings if the `column` or
        `to_date_column` contains strings instead of actual datetime objects.
        If None, pandas will infer the format.

    Returns
    -------
    pd.DataFrame
        DataFrame with the timedelta column in days.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"date": [pd.Timestamp("2021-01-01"),
    ... pd.Timestamp("2021-02-01")], "ref": [pd.Timestamp("2021-01-15"),
    ... pd.Timestamp("2021-02-15")]})
    >>> timedelta(df, "date", "days_to_ref", to_date_column="ref")
            date        ref  days_to_ref
    0 2021-01-01 2021-01-15           14
    1 2021-02-01 2021-02-15           14

    >>> today = pd.to_datetime("today")
    >>> df = pd.DataFrame({"birthdate": [today - pd.Timedelta(days=300),
    ... today - pd.Timedelta(days=250)]})
    >>> df['birthdate'] = df['birthdate'].dt.date
    >>> df = timedelta(df, "birthdate", "age_in_days")
    >>> df[['age_in_days']]
       age_in_days
    0          300
    1          250

    """
    dates = pd.to_datetime(df[column], format=fmt)

    if to_date_column:
        duration_col = (
            pd.to_datetime(df[to_date_column], format=fmt) - dates
        ).dt.days
    elif to_date:
        to_date = pd.Timestamp(to_date)
        duration_col = (to_date - dates).dt.days
    else:
        to_date = pd.to_datetime("today")
        duration_col = (to_date - dates).dt.days

    df[output_column] = duration_col

    return df


def calculate_age(
    df: pd.DataFrame,
    column: str,
    output_column: str = "age",
    fmt: str | None = None,
    keep_original: bool = True,
    reference_date: date | None = None,
) -> pd.DataFrame:
    """
    Calculate the calendar age in years from the birthdate column to a
    reference date (defaults to today).

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    column : str
        The name of the column containing birthdate information.
    output_column : str
        The name of the column to store the age.
    fmt : str | None, optional
        The format string to parse the birthdate column. If None, the format
        will be inferred.
    keep_original : bool, default True
        Whether to keep the original birthdate column in the DataFrame.
    reference_date : date | None, optional
        The date to use as the reference for calculating age. If None, today's
        date is used.

            Returns
    -------
    pd.DataFrame
        DataFrame with the calculated age column.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"birthdate": [pd.Timestamp("2000-01-01"),
    ... pd.Timestamp("1980-05-15")]})
    >>> df['birthdate'] = df['birthdate'].dt.date
    >>> calculate_age(df, "birthdate", "age", reference_date=date(2025, 1, 1))
        birthdate  age
    0  2000-01-01   25
    1  1980-05-15   44
    """
    if reference_date is None:
        reference_date = date.today()

    def compute_age(birthdate):
        return (
            reference_date.year
            - birthdate.year
            - (
                (reference_date.month, reference_date.day)
                < (birthdate.month, birthdate.day)
            )
        )

    birthdates = pd.to_datetime(df[column], format=fmt)
    df[output_column] = birthdates.apply(compute_age)

    if not keep_original:
        df.drop(columns=[column], inplace=True)

    return df
