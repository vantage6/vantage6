"""
Development script to create a directory on the host that will be mounted
into one of the development containers.
"""

import argparse
from pathlib import Path

from scripts.utils import replace_wsl_path


def create_mount_directory(dir_path: Path):
    """
    Create a directory on the host that will be mounted into one of the
    development containers.
    """
    dir_path = replace_wsl_path(dir_path)

    dir_path.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Create a mount directory")
    parser.add_argument("dir_path", type=Path, help="The directory to create")
    args = parser.parse_args()
    create_mount_directory(args.dir_path)


if __name__ == "__main__":
    main()
