from __future__ import annotations

from vantage6.common.context import AppContext
from vantage6.common.globals import InstanceType

from vantage6.cli.globals import (
    DEFAULT_API_SERVICE_SYSTEM_FOLDERS as S_FOL,
)


class HubContext(AppContext):
    """
    Hub context
    """

    def __init__(
        self, instance_name: str, system_folders: bool = S_FOL, is_sandbox: bool = False
    ):
        super().__init__(
            InstanceType.HUB,
            instance_name,
            system_folders=system_folders,
            is_sandbox=is_sandbox,
        )

    @classmethod
    def from_external_config_file(
        cls, path: str, system_folders: bool = S_FOL, in_container: bool = False
    ) -> HubContext:
        """
        Create a Hub context from an external configuration file.

        Parameters
        ----------
        path : str
            Path of the configuration file
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL
        in_container : bool, optional
            Whether the application is running inside a container, by default False

        Returns
        -------
        HubContext
            Hub context object
        """
        return super().from_external_config_file(
            path, InstanceType.HUB, system_folders, in_container
        )

    @classmethod
    def config_exists(
        cls, instance_name: str, system_folders: bool = S_FOL, is_sandbox: bool = False
    ) -> bool:
        """
        Check if a configuration file exists.

        Parameters
        ----------
        instance_name : str
            Name of the configuration instance, corresponds to the filename
            of the configuration file.
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL
        is_sandbox : bool, optional
            Whether the configuration is a sandbox configuration, by default False

        Returns
        -------
        bool
            Whether the configuration file exists or not
        """
        return super().base_config_exists(
            InstanceType.HUB,
            instance_name,
            system_folders=system_folders,
            is_sandbox=is_sandbox,
        )

    @classmethod
    def available_configurations(
        cls, system_folders: bool = S_FOL, is_sandbox: bool = False
    ) -> tuple[list, list]:
        """
        Find all available Hub configurations in the default folders.

        Parameters
        ----------
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL
        is_sandbox : bool, optional
            Whether the configuration is a sandbox configuration, by default False

        Returns
        -------
        tuple[list, list]
            The first list contains validated configuration files, the second
            list contains invalid configuration files.
        """
        return super().available_configurations(
            InstanceType.HUB, system_folders, is_sandbox
        )
