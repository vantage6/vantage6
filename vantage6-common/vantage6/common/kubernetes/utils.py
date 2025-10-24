import os


def running_in_pod() -> bool:
    """
    Detect if running inside a Kubernetes pod.

    Returns
    -------
    bool
        True if running inside a Kubernetes pod, False otherwise
    """
    # Check for Kubernetes service account
    return os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")
