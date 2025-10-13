from dataclasses import dataclass
from pathlib import Path


@dataclass
class NodeConfigCreationDetails:
    node_starting_port_number: int
    dev_dir: Path
    task_directory: str
    task_namespace: str


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
    wsl_reference_path = "/run/desktop/mnt/host/wsl"
    wsl_regular_path = "/mnt/wsl"
    if to_mnt_wsl and str(path).startswith(wsl_reference_path):
        path = Path(wsl_regular_path) / path.relative_to(wsl_reference_path)
    elif not to_mnt_wsl and str(path).startswith(wsl_regular_path):
        path = Path(wsl_reference_path) / path.relative_to(wsl_regular_path)
    return path
