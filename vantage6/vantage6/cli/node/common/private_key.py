"""
Helpers to store a node's private key in a Kubernetes secret.

The secret is created with the Kubernetes API rather than by the Helm chart, so that it
is kept when the node is stopped (``helm uninstall``) and only deleted when the node is
removed.
"""

import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from kubernetes import client as k8s_client
from kubernetes.client.exceptions import ApiException

from vantage6.common import base64s_to_bytes, bytes_to_base64s, info
from vantage6.common.encryption import RSACryptor
from vantage6.common.enum import StrEnumBase

from vantage6.cli.common.utils import create_kubernetes_secret
from vantage6.cli.context.node import NodeContext
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.utils_kubernetes import get_core_api_with_ssl_handling

PRIVATE_KEY_SECRET_KEY = "private_key.pem"


class KeyPolicy(StrEnumBase):
    """
    How to handle an existing private key secret and the organization's public key at
    HQ when storing a node's private key.

    - ``keep_existing``: keep the node's existing secret. If there is none, store the
      given key or generate one. The key must match HQ's public key, which is uploaded
      if HQ has none.
    - ``replace_node_key``: replace the node's secret. The key must still match HQ's
      public key, which is uploaded if HQ has none.
    - ``rotate_organization_key``: replace the node's secret and, after confirmation,
      the organization's public key at HQ. Other nodes and users of the organization
      then need the new private key.
    - ``local_only``: create the secret if it is missing, without contacting HQ. The
      key is checked against HQ when the node starts.
    """

    KEEP_EXISTING = "keep_existing"
    REPLACE_NODE_KEY = "replace_node_key"
    ROTATE_ORGANIZATION_KEY = "rotate_organization_key"
    LOCAL_ONLY = "local_only"


def private_key_secret_name(ctx: NodeContext) -> str:
    """
    Name of the Kubernetes secret that holds the node's private key.

    The node Helm chart mounts the secret by the same name, derived from the release
    name: ``{{ .Release.Name }}-private-key``.
    """
    return f"{ctx.helm_release_name}-private-key"


def validate_private_key_pem(pem: bytes) -> None:
    """
    Check that the given bytes are an unencrypted PEM-encoded private key.

    Raises
    ------
    ValueError
        If the bytes cannot be loaded as a private key
    """
    load_pem_private_key(pem, password=None, backend=default_backend())


def _public_key_bytes(pem: bytes) -> bytes:
    private_key = load_pem_private_key(pem, password=None, backend=default_backend())
    return RSACryptor.create_public_key_bytes(private_key)


def public_key_base64_from_pem(pem: bytes) -> str:
    """Derive the base64-encoded public key that HQ stores for the organization."""
    return bytes_to_base64s(_public_key_bytes(pem))


def public_key_matches(pem: bytes, hq_public_key: str) -> bool:
    """
    Check whether a private key belongs to the public key HQ has for the organization.

    Parameters
    ----------
    pem: bytes
        PEM-encoded private key
    hq_public_key: str
        Public key of the organization as returned by HQ
    """
    return _public_key_bytes(pem) == base64s_to_bytes(hq_public_key)


def _read_secret(
    core_api: k8s_client.CoreV1Api, name: str, namespace: str
) -> k8s_client.V1Secret | None:
    try:
        return core_api.read_namespaced_secret(name=name, namespace=namespace)
    except ApiException as exc:
        if exc.status == 404:
            return None
        raise


def read_private_key_secret(
    ctx: NodeContext, k8s_config: KubernetesConfig
) -> bytes | None:
    """
    Read the node's private key from its Kubernetes secret.

    Returns
    -------
    bytes | None
        The PEM-encoded private key, or None if the secret does not exist
    """
    core_api = get_core_api_with_ssl_handling(context=k8s_config.context)
    secret = _read_secret(core_api, private_key_secret_name(ctx), k8s_config.namespace)
    if secret is None:
        return None
    return base64.b64decode(secret.data[PRIVATE_KEY_SECRET_KEY])


def private_key_secret_exists(ctx: NodeContext, k8s_config: KubernetesConfig) -> bool:
    """Check whether the node's private key secret exists."""
    core_api = get_core_api_with_ssl_handling(context=k8s_config.context)
    secret = _read_secret(core_api, private_key_secret_name(ctx), k8s_config.namespace)
    return secret is not None


def write_private_key_secret(
    ctx: NodeContext, k8s_config: KubernetesConfig, pem: bytes
) -> None:
    """
    Store the node's private key in its Kubernetes secret, replacing an existing one.

    Parameters
    ----------
    ctx: NodeContext
        Context of the node
    k8s_config: KubernetesConfig
        Kubernetes configuration with the namespace to store the secret in
    pem: bytes
        PEM-encoded private key to store
    """
    core_api = get_core_api_with_ssl_handling(context=k8s_config.context)
    name = private_key_secret_name(ctx)
    namespace = k8s_config.namespace

    if _read_secret(core_api, name, namespace) is not None:
        info(f"Replacing existing private key secret '{name}'")
        core_api.delete_namespaced_secret(name=name, namespace=namespace)

    create_kubernetes_secret(
        core_api=core_api,
        secret_name=name,
        namespace=namespace,
        secret_data={PRIVATE_KEY_SECRET_KEY: pem.decode()},
    )
    info(f"Private key stored in Kubernetes secret '{name}' (namespace '{namespace}')")


def delete_private_key_secret(ctx: NodeContext, k8s_config: KubernetesConfig) -> bool:
    """
    Delete the node's private key secret.

    Returns
    -------
    bool
        True if a secret was deleted, False if it did not exist
    """
    core_api = get_core_api_with_ssl_handling(context=k8s_config.context)
    try:
        core_api.delete_namespaced_secret(
            name=private_key_secret_name(ctx), namespace=k8s_config.namespace
        )
    except ApiException as exc:
        if exc.status == 404:
            return False
        raise
    return True
