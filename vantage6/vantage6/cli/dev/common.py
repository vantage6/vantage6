import shutil
import subprocess
import sys

from vantage6.common import error


def check_devspace_installed() -> None:
    """Check if devspace is installed. Exits if not."""
    # Check if devspace command exists
    if shutil.which("devspace") is None:
        _message_devspace_not_installed()

    try:
        # Try to run devspace --version to verify it's working
        result = subprocess.run(
            ["devspace", "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            _message_devspace_not_installed()
    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        _message_devspace_not_installed()


def _message_devspace_not_installed() -> None:
    error(
        "❌ DevSpace command not found. Please ensure devspace is installed and in "
        "your PATH."
    )
    sys.exit(1)
