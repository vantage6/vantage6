import os
import platform


def running_in_pod() -> bool:
    """
    Detect if running inside a Kubernetes pod.

    Returns
    -------
    bool
        True if running inside a Kubernetes pod, False otherwise
    """
    # This environment variable is always set by kubelet
    return os.environ.get("KUBERNETES_SERVICE_HOST") is not None

def running_in_wsl() -> bool:
    """
    Detect if running inside a WSL environment.
    
    Returns
    -------
    bool
        True if running inside a WSL environment, False otherwise
    """
    release = platform.uname().release
    return platform.system() == "Linux" and (
        release.endswith('Microsoft') or release.endswith('microsoft-standard-WSL2')
    )

def running_on_windows() -> bool:
    """
    Detect if running on a Windows machine.
    
    Returns
    -------
    bool
        True if running on a Windows machine, False otherwise
    """
    return platform.system() == "Windows"