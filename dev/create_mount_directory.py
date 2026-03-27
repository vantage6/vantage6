"""
Development script to create a directory on the host that will be mounted
into one of the development containers.
"""

import argparse
from pathlib import Path

from vantage6.common.kubernetes.utils import running_in_wsl

from vantage6.cli.common.k8s_utils import run_kubectl_command
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.sandbox.populate.helpers.utils import replace_wsl_path


def _create_mount_directory_on_k8s_node(
    dir_path: Path, k8s_node_name: str
) -> None:
    """
    Ensure the mount path exists from the Kubernetes node filesystem perspective.
    Needed for Docker Desktop + WSL hostPath mounts.
    """
    run_kubectl_command(
        [
            "debug",
            f"node/{k8s_node_name}",
            "--image=busybox:latest",
            "--",
            "chroot",
            "/host",
            "sh",
            "-c",
            f"mkdir -p '{dir_path}'",
        ],
        KubernetesConfig(),
        use_k8s_config_namespace=False,
    )


def create_mount_directory(
    dir_path: Path,
    k8s_node_name: str | None = None,
):
    """
    Create a directory on the host that will be mounted into one of the
    development containers.
    """
    dir_path = replace_wsl_path(dir_path)

    dir_path.mkdir(parents=True, exist_ok=True)

    if running_in_wsl() and k8s_node_name:
        _create_mount_directory_on_k8s_node(dir_path, k8s_node_name)


def main():
    parser = argparse.ArgumentParser(description="Create a mount directory")
    parser.add_argument("dir_path", type=Path, help="The directory to create")
    parser.add_argument(
        "--k8s-node-name",
        type=str,
        default=None,
        help="Kubernetes node name for creating mount path from node filesystem",
    )
    args = parser.parse_args()
    create_mount_directory(args.dir_path, args.k8s_node_name)


if __name__ == "__main__":
    main()
