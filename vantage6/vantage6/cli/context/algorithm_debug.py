from __future__ import annotations

import os

from dataclasses import dataclass
from pathlib import Path

from vantage6.common.globals import NodeDefaults


@dataclass
class AlgorithmDebugConfig:
    """
    Configuration for algorithm debugging.

    Paths for algorithm source code, debugger, ports, etc

    Parameters
    ----------
    debug_dir : Path
        debugger directory (gdb, debugpy, runner script, etc)
    algo_source_dir : Path
        algorithm source code directory
    algo_dest_dir : Path
        algorithm destination directory on algorithm container
    base_dir : Path
        paths above can be relative, this is the base
    launcher : str
        launcher script path to run the debugger that will run the algorithm
    host : str
        host address the container binds to (docker)
    port_host : int
        port on host to bind to (docker)
    port_container : int
        target port on container (docker)
    validate : bool, optional
        whether to validate the configuration, by default True
    """

    debug_dir: Path  # debugger directory (gdb, debugpy, runner script, etc)
    algo_source_dir: Path  # algorithm source code directory
    algo_dest_dir: Path  # algorithm destination directory on algorithm container
    base_dir: Path  # paths above can be relative, this is the base
    launcher: str  # script to run the debugger that will run the algorithm
    host: str  # host address the container binds to (docker)
    port_host: int  # port on host to bind to (docker)
    port_container: int  # target port on container (docker)
    validate: bool = True  # whether to validate the configuration

    def __post_init__(self):
        if self.validate:
            self._validate()
        self._process()

    def _validate(self):
        """
        Check algorithm debugger options look correct

        Parameters
        ----------

        Returns
        -------
        bool
            False is debugger algorithm settings are incorrect,
            True otherwise or if no settings are present
        """
        debug_dir = self.debug_dir
        if not debug_dir.is_absolute():
            debug_dir = (self.base_dir / debug_dir).resolve()

        if not debug_dir.exists():
            raise ValueError(
                f"Debugger algorithm directory '{debug_dir}' does not exist."
            )

        # check launcher exists within debug_dir
        launcher = debug_dir / self.launcher
        if not launcher.exists():
            raise ValueError(
                f"Debugger algorithm launcher script '{launcher}' does not exist."
            )

        algo_source_dir = self.algo_source_dir
        if not algo_source_dir.is_absolute():
            algo_source_dir = (self.base_dir / self.algo_source_dir).resolve()

        if not algo_source_dir.exists():
            raise ValueError(
                f"Debugger algorithm: algorithm source directory '{algo_source_dir}' does not exist."
            )

        return True

    def _process(self):
        """
        Process algorithm debugger options
        """
        if not self.debug_dir.is_absolute():
            self.debug_dir = (self.base_dir / self.debug_dir).resolve()

        if not self.algo_source_dir.is_absolute():
            self.algo_source_dir = (self.base_dir / self.algo_source_dir).resolve()

    def docker_run_ports(self):
        """
        Generate a dictionary for Docker's `container.run` method to set up port forwarding.

        Returns
        -------
        dict
            Dictionary mapping container ports to host ports
        """
        return {self.port_container: (self.host, self.port_host)}

    def docker_run_command(self):
        """
        Generate appropiate command arguments for Docker's `container.run` method.
        """
        return str((self.debug_dir / self.launcher).resolve())

    @classmethod
    def from_config(
        cls, config: dict, base_dir: Path, validate: bool = True
    ) -> AlgorithmDebugConfig:
        """
        Create an AlgorithmDebugConfig instance from a `debugger_algorithm`
        config dictionary like the one used in the node config.

        Parameters
        ----------
        config : dict
            Configuration dictionary. See AlgorithmDebugConfig for required keys.
        base_dir : Path
            Base directory for relative paths
        validate : bool, optional
            Whether to validate the configuration, by default True
        """
        # minimal validation, keys must exist
        req_keys = [
            "debug_dir",
            "launcher",
            "host",
            "port_host",
            "port_container",
            "algo_source_dir",
            "algo_dest_dir",
        ]
        missing_keys = req_keys - config.keys()
        if missing_keys:
            raise ValueError(
                f"Missing keys in debugger_algorithm config: {missing_keys}"
            )

        # debug_dir and algo_source_dir can be overridden by an env var. Useful
        # if where config will be parsed is not original host filesystem
        # namespace (e.g. in a container)
        debug_dir = cls._get_path_from_env(
            NodeDefaults.ALGORITHM_DEBUG_DEBUGGER_DIR_ENV_VAR
        ) or Path(config["debug_dir"])
        algo_source_dir = cls._get_path_from_env(
            NodeDefaults.ALGORITHM_DEBUG_SOURCE_DIR_ENV_VAR
        ) or Path(config["algo_source_dir"])

        return cls(
            debug_dir=debug_dir,
            algo_source_dir=algo_source_dir,
            algo_dest_dir=Path(config["algo_dest_dir"]),
            base_dir=base_dir,
            launcher=Path(config["launcher"]),
            host=config["host"],
            port_host=config["port_host"],
            port_container=config["port_container"],
            validate=validate,
        )

    @staticmethod
    def _get_path_from_env(var: str) -> Path:
        """
        Get a path from an environment variable, if it exists.

        Parameters
        ----------
        var : str
            Environment variable name

        Returns
        -------
        Path
            Path from the environment variable, or None if the variable is not set
        """
        if var in os.environ:
            path = Path(os.environ[var])
            if not path.is_absolute():
                raise ValueError(f"Environment variable {var} must be an absolute path")
            return path
        return None
