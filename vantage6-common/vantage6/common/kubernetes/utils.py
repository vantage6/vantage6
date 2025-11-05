import os


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
