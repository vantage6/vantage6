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

    def get_database_uri(self) -> str:
        """
        Obtain the database uri from the environment or the configuration.

        Returns
        -------
        str
            string representation of the database uri
        """
        is_db_external = self.config["database"]["external"]
        if is_db_external:
            uri = self.config["database"]["uri"]
        else:
            db_conf = self.config["database"]
            uri = (
                f"postgresql://{db_conf['username']}:{db_conf['password']}@"
                f"{self.helm_release_name}-postgres-service:5432/{db_conf['name']}"
            )

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
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL

        Returns
        -------
        ServerContext
            Server context object
        """
        cls = super().from_external_config_file(path, server_type, system_folders)
        return cls
