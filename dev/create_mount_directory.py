# echo "Creating tasks folder"
# mkdir -p ${TASK_DIRECTORY}
"""
Development script to create a directory on the host that will be mounted
into one of the development containers.
"""

import argparse

from pathlib import Path


def create_mount_directory(dir: Path):
    """
    Create a directory on the host that will be mounted into one of the
    development containers.

    """
    # If the directory contains /run/desktop/mnt/host/wsl, this will be replaced
    # by /mnt/wsl: this is an idiosyncrasy of WSL (for more details, see
    # https://dev.to/nsieg/use-k8s-hostpath-volumes-in-docker-desktop-on-wsl2-4dcl)
    if str(dir).startswith("/run/desktop/mnt/host/wsl"):
        dir = Path("/mnt/wsl") / dir.relative_to("/run/desktop/mnt/host/wsl")

    dir.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Create a mount directory")
    parser.add_argument("dir", type=Path, help="The directory to create")
    args = parser.parse_args()
    create_mount_directory(args.dir)


if __name__ == "__main__":
    main()
