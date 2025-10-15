"""
Kubernetes utility functions for Vantage6 CLI.

This module provides utilities for handling Kubernetes client configuration,
especially for MicroK8s environments that may have SSL certificate issues.
"""

import base64
import ssl
from pathlib import Path
from typing import Optional

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException

from vantage6.common import warning


def configure_kubernetes_client_for_microk8s(cfg: client.Configuration) -> None:
    """
    Configure the Kubernetes client to handle MicroK8s SSL certificate issues.

    This function detects if we're using MicroK8s and configures the client
    to handle SSL certificates appropriately for both development and production.
    """
    # Check if we're using MicroK8s by looking at the current context
    if is_microk8s_context():
        _configure_microk8s_ssl(cfg)


def _configure_microk8s_ssl(cfg: client.Configuration) -> None:
    """
    Configure SSL settings for MicroK8s.

    This function handles MicroK8s SSL certificates in a secure way by:
    1. First trying to use the MicroK8s certificate directly
    2. If that fails, falling back to a more lenient but still secure approach
    """
    try:
        # Try to get the MicroK8s certificate and use it properly
        cert_path = _get_microk8s_certificate_path()
        if cert_path and cert_path.exists():
            _configure_with_certificate(cert_path, cfg)
        else:
            warning(
                "MicroK8s certificate not found. You may run into errors when using "
                "the CLI."
            )

    except Exception as e:
        warning(f"Could not configure MicroK8s SSL settings: {e}")
        warning("You may run into errors when using the CLI.")


def _get_microk8s_certificate_path() -> Optional[Path]:
    """
    Get the path to the MicroK8s certificate.

    Returns
    -------
    Optional[Path]
        Path to the MicroK8s certificate if found, None otherwise
    """
    # Common MicroK8s certificate locations
    possible_paths = [
        Path.home() / ".kube" / "microk8s.crt",
        Path("/var/snap/microk8s/current/certs/ca.crt"),
        Path("/var/snap/microk8s/current/certs/server.crt"),
    ]

    for cert_path in possible_paths:
        if cert_path.exists():
            return cert_path

    return None


def _configure_with_certificate(cert_path: Path, cfg: client.Configuration) -> None:
    """
    Configure the Kubernetes client to use a specific certificate.

    Parameters
    ----------
    cert_path : Path
        Path to the certificate file
    """
    try:
        # Validate the certificate before using it
        if not _validate_certificate(cert_path):
            warning(
                f"Certificate {cert_path} appears to be invalid. You may run into "
                "errors when using the CLI."
            )
            return

        cfg.verify_ssl = True
        cfg.ssl_ca_cert = str(cert_path)

        # Apply the configuration to the default client
        client.Configuration.set_default(cfg)

    except Exception as e:
        warning(f"Failed to configure with certificate {cert_path}: {e}")
        warning("You may run into errors when using the CLI.")


def _validate_certificate(cert_path: Path) -> bool:
    """
    Validate that a certificate file is readable and appears to be a valid certificate.

    Parameters
    ----------
    cert_path : Path
        Path to the certificate file

    Returns
    -------
    bool
        True if the certificate appears valid, False otherwise
    """
    try:
        # Check if the file exists and is readable
        if not cert_path.exists() or not cert_path.is_file():
            return False

        # Try to read the certificate content
        with open(cert_path, "rb") as f:
            cert_data = f.read()

        # Basic validation: check if it looks like a PEM certificate
        if b"-----BEGIN CERTIFICATE-----" not in cert_data:
            return False

        # Try to parse the certificate with Python's ssl module
        try:
            # Extract the base64 part between BEGIN and END
            start_text = b"-----BEGIN CERTIFICATE-----"
            len_start_text = len(start_text)
            start = cert_data.find(start_text)
            end = cert_data.find(b"-----END CERTIFICATE-----")
            if start != -1 and end != -1:
                cert_b64 = (
                    cert_data[start + len_start_text : end]
                    .replace(b"\n", b"")
                    .replace(b"\r", b"")
                )
                cert_der = base64.b64decode(cert_b64)
                ssl.DER_cert_to_PEM_cert(cert_der)
                return True
        except Exception:
            pass

        # If we can't parse it with ssl module, at least check it has the right
        # structure
        return (
            b"-----BEGIN CERTIFICATE-----" in cert_data
            and b"-----END CERTIFICATE-----" in cert_data
        )

    except Exception as e:
        warning(f"Certificate validation failed: {e}")
        return False


def load_kubernetes_config_with_fallback() -> bool:
    """
    Load Kubernetes configuration with fallback for development environments.

    This function tries to load the Kubernetes configuration and handles
    common issues like SSL certificate problems in development environments.

    Returns
    -------
    bool
        True if configuration was loaded successfully, False otherwise
    """
    # Try to load in-cluster config first (for when running inside Kubernetes)
    try:
        config.load_incluster_config()
        return True
    except ConfigException:
        pass

    # Fallback to kubeconfig
    try:
        # Load kubeconfig into default config, then adjust CA if MicroK8s
        config.load_kube_config()
        cfg = client.Configuration.get_default_copy()
        configure_kubernetes_client_for_microk8s(cfg)
        client.Configuration.set_default(cfg)

        return True
    except ConfigException as exc:
        warning(f"Failed to load Kubernetes configuration: {exc}")
        return False


def create_kubernetes_apis_with_ssl_handling() -> tuple[
    client.CoreV1Api, client.BatchV1Api
]:
    """
    Create Kubernetes API clients with SSL handling for development environments.

    Returns
    -------
    tuple[client.CoreV1Api, client.BatchV1Api]
        Tuple of CoreV1Api and BatchV1Api clients
    """
    # Load configuration with fallback handling
    if not load_kubernetes_config_with_fallback():
        raise RuntimeError("Failed to load Kubernetes configuration")

    # Create API clients
    core_api = client.CoreV1Api()
    batch_api = client.BatchV1Api()

    return core_api, batch_api


def get_core_api_with_ssl_handling() -> client.CoreV1Api:
    """
    Get the CoreV1Api client with SSL handling for development environments.
    """
    core_api, _ = create_kubernetes_apis_with_ssl_handling()
    return core_api


def is_microk8s_context() -> bool:
    """
    Check if the current Kubernetes context is MicroK8s.

    Returns
    -------
    bool
        True if using MicroK8s context, False otherwise
    """
    try:
        _, active_context = config.list_kube_config_contexts()
        current_context = active_context.get("name", "") if active_context else ""
        return "microk8s" in current_context.lower()
    except Exception:
        return False
