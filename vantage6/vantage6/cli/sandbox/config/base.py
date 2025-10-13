from pathlib import Path

import yaml

from vantage6.common.globals import InstanceType

from vantage6.cli.context import select_context_class
from vantage6.cli.sandbox.populate.helpers.utils import replace_wsl_path


class BaseSandboxConfigManager:
    """
    Base class for sandbox configuration managers.

    Parameters
    ----------
    server_name : str
        Name of the server.
    custom_data_dir : Path | None
        Path to the custom data directory. Useful on WSL because of mount issues for
        default directories.
    """

    def __init__(self, server_name: str, custom_data_dir: Path | None) -> None:
        self.server_name = server_name
        self.custom_data_dir = Path(custom_data_dir) if custom_data_dir else None

    @staticmethod
    def _read_extra_config_file(extra_config_file: Path | None) -> dict:
        """Reads extra configuration file.

        Parameters
        ----------
        extra_config_file : Path | None
            Path to file with additional configuration.

        Returns
        -------
        dict
            Extra configuration parsed from YAML. Empty dict if none provided.
        """
        if extra_config_file:
            with open(extra_config_file, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
                if not isinstance(loaded, dict):
                    # Ensure we always return a dictionary
                    return {"value": loaded}
                return loaded
        return {}

    def _create_and_get_data_dir(
        self, instance_type: InstanceType, is_data_folder: bool = False
    ) -> Path:
        """
        Create and get the data directory.

        Parameters
        ----------
        instance_type: InstanceType
            Type of vantage6 component
        is_data_folder: bool
            Whether or not to create the data folder or a config folder. This is only
            used for node databases. Default is False.

        Returns
        -------
        Path
            Path to the data directory
        """
        ctx_class = select_context_class(instance_type)
        folders = ctx_class.instance_folders(
            instance_type=InstanceType.SERVER,
            instance_name=self.server_name,
            system_folders=False,
        )
        main_data_dir = (
            Path(folders["dev"]) if not self.custom_data_dir else self.custom_data_dir
        )

        if instance_type == InstanceType.SERVER:
            data_dir = main_data_dir / self.server_name / "server"
        elif instance_type == InstanceType.ALGORITHM_STORE:
            data_dir = main_data_dir / self.server_name / "store"
        elif instance_type == InstanceType.NODE:
            if is_data_folder:
                last_subfolder = "data"
            else:
                last_subfolder = "node"
            data_dir = main_data_dir / self.server_name / last_subfolder
        else:
            raise ValueError(f"Invalid instance type to get data dir: {instance_type}")

        # For the directory to be created, ensure that if a WSL path is used, the path
        # is converted to /mnt/wsl to create the directory on the host (not
        # /run/desktop/mnt/host/wsl as will raise non-existent directory errors)
        data_dir = replace_wsl_path(data_dir, to_mnt_wsl=True)
        data_dir.mkdir(parents=True, exist_ok=True)
        # now ensure that the wsl path is properly replaced to /run/desktop/mnt/host/wsl
        # if it is a WSL path, because that path will be used in the node configuration
        # files and is required to successfully mount the volumes.
        return replace_wsl_path(data_dir, to_mnt_wsl=False)
