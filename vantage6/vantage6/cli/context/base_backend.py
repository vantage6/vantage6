from __future__ import annotations

from vantage6.common.context import AppContext

from vantage6.cli.globals import (
    DEFAULT_API_SERVICE_SYSTEM_FOLDERS as S_FOL,
    BackendType,
)


class BaseBackendContext(AppContext):
    """
    Base context for a vantage6 HQ or algorithm store

    Contains functions that the HQContext and AlgorithmStoreContext have
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
        # within container, the uri is set in the config file
        if self.in_container:
            return self.config.get("uri")

        # outside container, the uri is set in the values.yaml in a different location
        is_db_external = self.config.get("database", {}).get("external", False)
        if is_db_external:
            uri = self.config["database"]["uri"]
        else:
            db_conf = self.config["database"]
            uri = (
                f"postgresql://{db_conf['username']}:{db_conf['password']}@"
                f"{self.helm_release_name}-postgres:5432/{db_conf['name']}"
            )

        return uri

    @classmethod
    def from_external_config_file(
        cls,
        path: str,
        backend_type: BackendType,
        system_folders: bool = S_FOL,
        in_container: bool = False,
    ) -> BaseBackendContext:
        """
        Create a backend context from an external configuration file. External
        means that the configuration file is not located in the default folders
        but its location is specified by the user.

        Parameters
        ----------
        path : str
            Path of the configuration file
        backend_type : BackendType
            Type of backend, either 'hq' or 'algorithm-store'
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL
        in_container : bool, optional
            Whether the application is running inside a container, by default False

        Returns
        -------
        HQContext | AlgorithmStoreContext
            Base backend context object
        """
        cls = super().from_external_config_file(
            path, backend_type, system_folders, in_container
        )
        return cls
