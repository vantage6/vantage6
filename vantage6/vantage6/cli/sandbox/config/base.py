from pathlib import Path

from vantage6.common.globals import InstanceType

from vantage6.cli.context import select_context_class
from vantage6.cli.sandbox.populate.helpers.utils import replace_wsl_path


class BaseSandboxConfigManager:
    """
    Base class for sandbox configuration managers.
    """

    def __init__(self, server_name: str, custom_data_dir: Path | None) -> None:
        self.server_name = server_name
        self.custom_data_dir = custom_data_dir

    @staticmethod
    def _read_extra_config_file(extra_config_file: Path | None) -> str:
        """Reads extra configuration file.

        Parameters
        ----------
        extra_config_file : Path | None
            Path to file with additional configuration.

        Returns
        -------
        str
            Extra configuration file content
        """
        if extra_config_file:
            # read the YAML file as string, so it can be appended to the
            # configuration easily
            with open(extra_config_file, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def _create_and_get_data_dir(self, instance_type: InstanceType) -> Path:
        """
        Create and get the data directory.
        """
        ctx_class = select_context_class(instance_type)
        folders = ctx_class.instance_folders(
            instance_type=InstanceType.SERVER,
            instance_name=self.server_name,
            system_folders=False,
        )

        if instance_type == InstanceType.SERVER:
            subfolder = self.custom_data_dir / self.server_name / "server"
        elif instance_type == InstanceType.ALGORITHM_STORE:
            subfolder = self.custom_data_dir / self.server_name / "store"
        elif instance_type == InstanceType.NODE:
            subfolder = self.custom_data_dir / self.server_name / "node"
        else:
            raise ValueError(f"Invalid instance type to get data dir: {instance_type}")
        if self.custom_data_dir is not None:
            data_dir = replace_wsl_path(
                self.custom_data_dir / subfolder, to_mnt_wsl=True
            )
        else:
            data_dir = Path(folders["dev"]) / self.server_name / subfolder
        data_dir.mkdir(parents=True, exist_ok=True)
        # now ensure that the wsl path is properly replaced to /run/desktop/mnt/host/wsl
        # if it is a WSL path
        return replace_wsl_path(data_dir, to_mnt_wsl=False)
