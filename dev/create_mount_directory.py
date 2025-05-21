"""
Development script to create a directory on the host that will be mounted
into one of the development containers.
"""

import argparse

from pathlib import Path


def create_mount_directory(dir_path: Path):
    """
    Create a directory on the host that will be mounted into one of the
    development containers.
    """
    # If the directory contains /run/desktop/mnt/host/wsl, this will be replaced
    # by /mnt/wsl: this is an idiosyncrasy of WSL (for more details, see
    # https://dev.to/nsieg/use-k8s-hostpath-volumes-in-docker-desktop-on-wsl2-4dcl)
    wsl_reference_path = "/run/desktop/mnt/host/wsl"
    wsl_regular_path = "/mnt/wsl"
    if str(dir_path).startswith(wsl_reference_path):
        dir_path = Path(wsl_regular_path) / dir_path.relative_to(wsl_reference_path)

    dir_path.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Create a mount directory")
    parser.add_argument("dir_path", type=Path, help="The directory to create")
    args = parser.parse_args()
    create_mount_directory(args.dir_path)


if __name__ == "__main__":
    main()
