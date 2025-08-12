import os
from functools import wraps

import pandas as pd

from vantage6.common.globals import (
    DATAFRAME_BETWEEN_GROUPS_SEPARATOR,
    DATAFRAME_MULTIPLE_KEYWORD,
    DATAFRAME_WITHIN_GROUP_SEPARATOR,
    ContainerEnvNames,
)

from vantage6.algorithm.tools.exceptions import UserInputError
from vantage6.algorithm.tools.util import error, info, warn


def _get_user_dataframes() -> list[str]:
    """
    Get the database names that the user requested from the environment

    Returns
    -------
    list[list[str]]
        List of database names, each list contains the names of the databases
        that are required for the argument.
    """
    dfs = os.environ[ContainerEnvNames.USER_REQUESTED_DATAFRAMES.value]

    data_arguments = dfs.split(DATAFRAME_BETWEEN_GROUPS_SEPARATOR)
    return [arg.split(DATAFRAME_WITHIN_GROUP_SEPARATOR) for arg in data_arguments]


def _read_df_from_disk(df_name: str) -> pd.DataFrame:
    """
    Load data from a dataframe file

    Parameters
    ----------
    df_name : str
        Label of the database to load

    Returns
    -------
    pd.DataFrame
        Data from the database
    """
    # Load the dataframe by the user specified df name. The dataframes are always stored
    # in the session folder, which is set by the vantage6 node. The label is the name of
    # the dataframe file, which is set by the user when creating the task.
    dataframe_folder = os.environ[ContainerEnvNames.SESSION_FOLDER.value]
    dataframe_file = os.path.join(dataframe_folder, f"{df_name}.parquet")
    info(f"Using '{dataframe_file}' with dataframe name '{df_name}' as database")

    return pd.read_parquet(dataframe_file)


def dataframe(*sources: str | int) -> callable:
    """
    Decorator that adds algorithm data to a function

    By adding `@dataframe()` to a function, one or several pandas dataframes will be
    added to the front of the argument list. This data will be read from the
    databases that the user who creates the task provides.

    Note that the user should provide exactly as many databases as the
    decorated function requires when they create the task.

    There is one reserved argument `mock_data` in the function to be
    decorated. If this argument is provided, the decorator will add this
    mocked data to the front of the argument list, instead of reading in the
    data from the databases.

    Parameters
    ----------
    sources: str | int
        Number of the dataframe to load. It can either be a number to indicate the
        number of dataframes to load or a string "multiple" to indicate that multiple
        dataframes need to be supplied as a single argument.

    Returns
    -------
    callable
        Decorated function

    Examples
    --------
    >>> @dataframe(2)
    >>> def my_algorithm(first_df: pd.DataFrame, second_df: pd.DataFrame,
    >>>                  <other arguments>):
    >>>     pass

    >>> @dataframe("multiple", 2)
    >>> def my_algorithm(dfs: dict[str, pd.DataFrame], first_df: pd.DataFrame,
    >>>                  second_df: pd.DataFrame, <other arguments>):
    >>>     pass

    >>> @dataframe("multiple", 1, "multiple")
    >>> def my_algorithm(dfs: dict[str, pd.DataFrame], first_df: pd.DataFrame,
    >>>                  dfs_2: dict[str, pd.DataFrame], <other arguments>):
    >>>     pass
    """
    if not sources:
        sources = (1,)

    def protection_decorator(func: callable, *args, **kwargs) -> callable:
        @wraps(func)
        def decorator(
            *args,
            mock_data: list[dict[str, pd.DataFrame] | pd.DataFrame] | None = None,
            **kwargs,
        ) -> callable:
            """
            Wrap the function with the data

            Parameters
            ----------
            mock_data : list[dict[str, pd.DataFrame] | pd.DataFrame]
                Mock data to use instead of the regular data. The list contains data
                for each argument that the function requires. For example, if the
                decorator is used as @dataframe(1, 2), the mock_data should be a list
                with two dataframes. If the decorator is used as
                `@dataframe("multiple")`, the mock_data should be a list of
                dictionaries with the dataframe names as keys and the dataframes as
                values.
            """

            if mock_data is not None:
                return func(*mock_data, *args, **kwargs)

            # get the dataframe names that the user requested
            dataframes_grouped = _get_user_dataframes()

            # check if user provided enough databases
            number_of_expected_arguments = 0
            for source in sources:
                if isinstance(source, int):
                    number_of_expected_arguments += source
                else:  # "multiple" requires one argument (of type list)
                    number_of_expected_arguments += 1

            if len(dataframes_grouped) < number_of_expected_arguments:
                error(
                    f"Algorithm requires {number_of_expected_arguments} databases "
                    f"but only {len(dataframes_grouped)} were provided. "
                    "Exiting..."
                )
                exit(1)
            elif len(dataframes_grouped) > number_of_expected_arguments:
                warn(
                    f"Algorithm requires only {number_of_expected_arguments} databases"
                    f", but {len(dataframes_grouped)} were provided. Using the "
                    f"first {number_of_expected_arguments} databases."
                )

            # read the data from the database(s)
            idx_dataframes = 0
            for source in sources:
                # if the source is not "multiple", we can just add the first (and only)
                # dataframe to the arguments
                if isinstance(source, int):
                    for _ in range(source):
                        requested_dataframes = dataframes_grouped[idx_dataframes]
                        df = _read_df_from_disk(requested_dataframes[0])
                        idx_dataframes += 1
                        args = (df, *args)
                elif str(source).lower() != DATAFRAME_MULTIPLE_KEYWORD:
                    requested_dataframes = dataframes_grouped[idx_dataframes]
                    data_ = {
                        df_name: _read_df_from_disk(df_name)
                        for df_name in requested_dataframes
                    }
                    idx_dataframes += 1
                    args = (data_, *args)
                else:
                    raise UserInputError(
                        f"Unrecognized argument '{source}' in dataframe decorator. "
                        "Please use 'multiple' or a number of dataframes to load."
                    )

            return func(*args, **kwargs)

        # set attribute that this function is wrapped in a data decorator
        decorator.vantage6_dataframe_decorated = True
        return decorator

    return protection_decorator


def dataframes(func: callable) -> callable:
    """
    Decorator that adds multiple pandas dataframes to a function

    By adding `@dataframes` to a function, multiple pandas dataframes will be
    added to the front of the argument list. This data will be read from the
    databases that the user who creates the task provides.
    """
    info("Using dataframes decorator")
    return dataframe(DATAFRAME_MULTIPLE_KEYWORD)(func)
