from __future__ import annotations

from vantage6.common.context import AppContext
from vantage6.common.globals import InstanceType

from vantage6.cli import __version__
from vantage6.cli.configuration_manager import AuthConfigurationManager
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS as S_FOL


class AuthContext(AppContext):
    """
    Context class for the keycloak authentication server.

    Parameters
    ----------
    instance_name : str
        Name of the configuration instance, corresponds to the filename
        of the configuration file.
    system_folders : bool, optional
        System wide or user configuration, by default S_FOL
    """

    # The auth configuration manager is aware of the structure of the auth
    # configuration file and makes sure only valid configuration can be loaded.
    INST_CONFIG_MANAGER = AuthConfigurationManager

    def __init__(
        self,
        instance_name: str,
        system_folders: bool = S_FOL,
    ):
        super().__init__(
            InstanceType.AUTH,
            instance_name,
            system_folders=system_folders,
        )
        self.log.info("vantage6 version '%s'", __version__)

    @classmethod
    def from_external_config_file(
        cls, path: str, system_folders: bool = S_FOL
    ) -> AuthContext:
        """
        Create a server context from an external configuration file. External
        means that the configuration file is not located in the default folders
        but its location is specified by the user.

        Parameters
        ----------
        path : str
            Path of the configuration file
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL

        Returns
        -------
        ServerContext
            Server context object
        """
        return super().from_external_config_file(
            path,
            InstanceType.AUTH,
            system_folders,
        )

    @classmethod
    def config_exists(cls, instance_name: str, system_folders: bool = S_FOL) -> bool:
        """
        Check if a configuration file exists.

        Parameters
        ----------
        instance_name : str
            Name of the configuration instance, corresponds to the filename
            of the configuration file.
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL

        Returns
        -------
        bool
            Whether the configuration file exists or not
        """
        return super().config_exists(
            InstanceType.AUTH, instance_name, system_folders=system_folders
        )

    @classmethod
    def available_configurations(
        cls, system_folders: bool = S_FOL
    ) -> tuple[list, list]:
        """
        Find all available auth configurations in the default folders.

        Parameters
        ----------
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL

        Returns
        -------
        tuple[list, list]
            The first list contains validated configuration files, the second
            list contains invalid configuration files.
        """
        return super().available_configurations(InstanceType.AUTH, system_folders)
