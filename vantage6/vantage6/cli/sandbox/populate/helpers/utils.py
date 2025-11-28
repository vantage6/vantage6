from dataclasses import dataclass
from pathlib import Path

from vantage6.common.kubernetes.utils import running_on_windows


@dataclass
class NodeConfigCreationDetails:
    node_starting_port_number: int
    dev_dir: Path
    task_directory: str
    task_namespace: str
    prometheus_enabled: bool = False


def path_to_str(path: Path) -> str:
    """
    Convert a path, either Linux or Windows, to a Linux-style string representation of the path.

    Parameters
    ----------
    path: Path
        Path to convert.

    Returns
    -------
    str
        Linux-style string path.
    """
    return str(path).replace("\\", "/")


def replace_wsl_path(path: Path, to_mnt_wsl: bool = True) -> Path:
    """
    Replace the WSL path with the regular path.

    If the directory contains /run/desktop/mnt/host/wsl, this will be replaced
    by /mnt/wsl: this is an idiosyncrasy of WSL (for more details, see
    https://dev.to/nsieg/use-k8s-hostpath-volumes-in-docker-desktop-on-wsl2-4dcl)

    Parameters
    ----------
    path: Path
        Path to replace.
    to_mnt_wsl: bool
        If True, the path will be replaced from the /run/desktop/mnt/host/wsl path to
        the /mnt/wsl path. If false, vice versa. By default, it is False.
    """
    # wsl_path_from_windows = r"\\wsl$\Ubuntu\mnt\wsl"
    wsl_reference_path = "/run/desktop/mnt/host/wsl"
    wsl_regular_path = "/mnt/wsl" if not running_on_windows else "//wsl$/Ubuntu/mnt/wsl"

    # # for windows WSL paths, first convert to a regular WSL path. This must only be done
    # # if we want a /run/desktop path because the directory /mnt/wsl in Windows must actually
    # # be the original \\wsl$\Ubuntu\mnt\wsl for Windows to interact with it
    # if not to_mnt_wsl and str(path).startswith(wsl_path_from_windows):
    #     path = Path(wsl_regular_path) / path.relative_to(wsl_path_from_windows)

    if to_mnt_wsl and path_to_str(path).startswith(wsl_reference_path):
        path = Path(wsl_regular_path) / path.relative_to(wsl_reference_path)
    elif not to_mnt_wsl and path_to_str(path).startswith(wsl_regular_path):
        path = Path(wsl_reference_path) / path.relative_to(wsl_regular_path)
    return path


def str_replace_wsl_path(path: Path, to_mnt_wsl: bool = True) -> Path:
    return path_to_str(replace_wsl_path(path, to_mnt_wsl))
