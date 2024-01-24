from __future__ import annotations

import os.path

from sqlalchemy.engine.url import make_url

from vantage6.common.context import AppContext
from vantage6.cli.globals import (
    DEFAULT_SERVER_SYSTEM_FOLDERS as S_FOL,
    ServerType,
)


class BaseServerContext(AppContext):
    """
    Base context for a vantage6 server or algorithm store server

    Contains functions that the ServerContext and AlgorithmStoreContext have
    in common.
    """

    def get_database_uri(self, db_env_var: str) -> str:
        """
        Obtain the database uri from the environment or the configuration.

        Parameters
        ----------
        db_env_var : str
            Name of the environment variable that contains the database uri

        Returns
        -------
        str
            string representation of the database uri
        """
        uri = os.environ.get(db_env_var) or self.config["uri"]
        url = make_url(uri)

        if url.host is None and not os.path.isabs(url.database):
            # We're dealing with a relative path here of a local database, when
            # we're running the server outside of docker. Therefore we need to
            # prepend the data directory to the database name, but after the
            # driver name (e.g. sqlite:////db.sqlite ->
            # sqlite:////data_dir>/db.sqlite)

            # find index of database name
            idx_db_name = str(url).find(url.database)

            # add the datadir to the right location in the database uri
            return str(url)[:idx_db_name] + str(self.data_dir / url.database)

        return uri

    @classmethod
    def from_external_config_file(
        cls,
        path: str,
        server_type: ServerType,
        config_name_env_var: str,
        system_folders: bool = S_FOL,
    ) -> BaseServerContext:
        """
        Create a server context from an external configuration file. External
        means that the configuration file is not located in the default folders
        but its location is specified by the user.

        Parameters
        ----------
        path : str
            Path of the configuration file
        server_type : ServerType
            Type of server, either 'server' or 'algorithm-store'
        config_name_env_var : str
            Name of the environment variable that contains the name of the
            configuration
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL

        Returns
        -------
        ServerContext
            Server context object
        """
        cls = super().from_external_config_file(path, server_type, system_folders)
        # if we are running a server in a docker container, the name is taken
        # from the name of the config file (which is usually a default). Get
        # the config name from environment if it is given.
        cls.name = os.environ.get(config_name_env_var) or cls.name
        return cls
