import os
import pandas as pd

from functools import wraps

from vantage6.common.globals import ContainerEnvNames
from vantage6.algorithm.tools.util import info, error, warn


def _get_user_dataframes() -> list[str]:
    """
    Get the database names that the user requested from the environment

    Returns
    -------
    list[str]
        List of database names
    """
    dfs = os.environ[ContainerEnvNames.USER_REQUESTED_DATAFRAMES.value]
    return dfs.split(",")


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


def data(number_of_databases: int = 1) -> callable:
    """
    Decorator that adds algorithm data to a function

    By adding `@data()` to a function, one or several pandas dataframes will be
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
    number_of_databases: int
        Number of data sources to load. These will be loaded in order by which
        the user provided them. Default is 1.

    Returns
    -------
    callable
        Decorated function

    Examples
    --------
    >>> @data(number_of_databases=2)
    >>> def my_algorithm(first_df: pd.DataFrame, second_df: pd.DataFrame,
    >>>                  <other arguments>):
    >>>     pass
    """

    def protection_decorator(func: callable, *args, **kwargs) -> callable:
        @wraps(func)
        def decorator(
            *args, mock_data: list[pd.DataFrame] = None, **kwargs
        ) -> callable:
            """
            Wrap the function with the data

            Parameters
            ----------
            mock_data : list[pd.DataFrame]
                Mock data to use instead of the regular data
            """

            if mock_data is not None:
                return func(*mock_data, *args, **kwargs)

            # get the dataframe names that the user requested
            dataframes = _get_user_dataframes()

            # check if user provided enough databases
            if len(dataframes) < number_of_databases:
                error(
                    f"Algorithm requires {number_of_databases} databases "
                    f"but only {len(dataframes)} were provided. "
                    "Exiting..."
                )
                exit(1)
            elif len(dataframes) > number_of_databases:
                warn(
                    f"Algorithm requires only {number_of_databases} databases"
                    f", but {len(dataframes)} were provided. Using the "
                    f"first {number_of_databases} databases."
                )

            for i in range(number_of_databases):

                dataframe_name = dataframes[i]
                # read the data from the database
                info("Reading dataframe")
                data_ = _read_df_from_disk(dataframe_name)

                # add the data to the arguments
                args = (data_, *args)

            return func(*args, **kwargs)

        # set attribute that this function is wrapped in a data decorator
        decorator.wrapped_in_data_decorator = True
        return decorator

    return protection_decorator
