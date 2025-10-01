from pathlib import Path


def replace_wsl_path(path: Path) -> Path:
    """
    Replace the WSL path with the regular path.

    If the directory contains /run/desktop/mnt/host/wsl, this will be replaced
    by /mnt/wsl: this is an idiosyncrasy of WSL (for more details, see
    https://dev.to/nsieg/use-k8s-hostpath-volumes-in-docker-desktop-on-wsl2-4dcl)
    """
    wsl_reference_path = "/run/desktop/mnt/host/wsl"
    wsl_regular_path = "/mnt/wsl"
    if str(path).startswith(wsl_reference_path):
        path = Path(wsl_regular_path) / path.relative_to(wsl_reference_path)
    return path
