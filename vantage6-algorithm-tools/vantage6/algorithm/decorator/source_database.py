import os

from functools import wraps
from vantage6.common import error
from vantage6.common.globals import ContainerEnvNames
from vantage6.algorithm.tools.util import get_env_var


def source_database(func) -> callable:
    @wraps(func)
    def decorator(
        *args, mock_uri: str | None = None, mock_type: str | None = None, **kwargs
    ) -> callable:
        """
        This decorator provides a the source database connection details to the
        function. This can be used to create a data extraction function.

        The user can request different databases that correspond to the different data
        sources that are available at each node. This decorator should be used in
        combination with the `data_extraction` decorator. This `@source_database`
        decorator relies on certain environment variables, that are validated by the
        `@data_extraction` decorator.

        Parameters
        ----------
        mock_uri : str
            Mock URI to use instead of the regular URI
        mock_type : str
            Mock type to use, e.g. `csv`, `excel`, `other`, etc.

        Returns
        -------
        dict
            Dictionary containing the connection details

        Examples
        --------
        For example, for a PostgreSQL database. The connection details are retrieved by
        the node from the environment variables and passed on to the algorithm
        container. This always follows the `DATABASE_*` naming convention.

        For example when the nodes reads the following environment for database A, and
        the user requests database `A`:
        ```bash
        DATABASE_A_URI="postgresql://host:port/database"
        DATABASE_A_USERNAME="postgresql"
        DATABASE_A_PASSWORD="password"
        DATABASE_A_OTHER_DETAILS="..."
        ```

        Then the algorithm container will pass the following environment variables to
        the algorithm (note that the `A_` annotation is removed):
        ```bash
        DATABASE_URI="postgresql://host:port/database"
        DATABASE_USERNAME="postgresql"
        DATABASE_PASSWORD="password"
        DATABASE_SOME_OTHER_PARAMETER="..."
        ```

        The algorithm can then use these environment variables to connect to the
        database:

        ```python
        >>> @data_extraction
        >>> @source_database
        >>> def my_function(connection_details: str):
        >>>     print(connection_details)
        {
            "uri": "postgresql://host:port/database",
            "username": "postgresql",
            "password": "password",
            "some_other_parameter": "..."
        }
        ```
        """
        connection_details = {}

        # At least need the URI and type needs to be provided by the node
        uri = get_env_var(ContainerEnvNames.DATABASE_URI.value, mock_uri)
        type_ = get_env_var(ContainerEnvNames.DATABASE_TYPE.value, mock_type)
        if not uri:
            error("No database URI provided. Exiting...")
            exit(1)
        if not type_:
            error("No database type provided. Exiting...")
            exit(1)

        connection_details["uri"] = uri
        connection_details["type"] = type_

        # Get the other details
        for key in os.environ:
            if key.startswith(ContainerEnvNames.DB_PARAM_PREFIX.value):
                connection_details[
                    key.replace(ContainerEnvNames.DB_PARAM_PREFIX.value, "")
                ] = os.environ[key]

        return func(connection_details, *args, **kwargs)

    return decorator
