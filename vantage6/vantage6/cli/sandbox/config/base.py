from pathlib import Path


class BaseSandboxConfigManager:
    """
    Base class for sandbox configuration managers.
    """

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
