"""
Development script to copy the node test datasets from this repository to the
directory on the host that is mounted into the node containers.

On WSL the mount path points outside of the repository (see DEV_MOUNT_BASE_PATH
in devspace.yaml), and /mnt/wsl is wiped whenever WSL restarts. The datasets
therefore have to be copied there again before every deployment. On other
systems the mount path is the repository's dev folder, so nothing is copied.
"""

import argparse
import shutil
from pathlib import Path

from vantage6.cli.sandbox.populate.helpers.utils import replace_wsl_path

from create_mount_directory import create_mount_directory

SOURCE_DIR = Path(__file__).parent


def copy_test_data(dest_dir: Path, file_names: list[str]):
    """
    Copy the test datasets to the directory that is mounted into the node
    containers.

    Files that are already present in the destination are left untouched, so
    that custom datasets are never overwritten.
    """
    dest_dir = replace_wsl_path(dest_dir)
    create_mount_directory(dest_dir)

    for file_name in file_names:
        source = SOURCE_DIR / file_name
        destination = dest_dir / file_name

        if not source.exists():
            print(f"  Warning: '{source}' does not exist, skipping it")
            continue

        if destination.exists():
            print(f"  '{destination}' already exists, skipping it")
            continue

        shutil.copy2(source, destination)
        print(f"  Copied '{source}' to '{destination}'")


def main():
    parser = argparse.ArgumentParser(description="Copy the node test datasets")
    parser.add_argument(
        "dest_dir", type=Path, help="The directory to copy the datasets to"
    )
    parser.add_argument("file_names", nargs="+", help="The datasets to copy")
    args = parser.parse_args()
    copy_test_data(args.dest_dir, args.file_names)


if __name__ == "__main__":
    main()
