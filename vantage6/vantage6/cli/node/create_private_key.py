import sys
from pathlib import Path

import click
import questionary as q
import requests
from kubernetes.client.exceptions import ApiException
from urllib3.exceptions import HTTPError

from vantage6.common import debug, error, info, warning
from vantage6.common.client.client_base import ClientBase
from vantage6.common.encryption import RSACryptor
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import extract_name_and_is_sandbox
from vantage6.cli.configuration_create import select_configuration_questionnaire
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
from vantage6.cli.k8s_config import KubernetesConfig, select_k8s_config
from vantage6.cli.node.common import create_client_and_authenticate
from vantage6.cli.node.common.private_key import (
    private_key_secret_name,
    public_key_base64_from_pem,
    public_key_matches,
    read_private_key_secret,
    validate_private_key_pem,
    write_private_key_secret,
)

K8S_ERRORS = (RuntimeError, ApiException, HTTPError)


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option(
    "-c",
    "--config",
    default=None,
    help="Absolute path to configuration-file; overrides NAME",
)
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Search for configuration in system folders rather than user folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Search for configuration in user folders rather than "
    "system folders. This is the default",
)
@click.option(
    "--no-upload",
    "upload",
    flag_value=False,
    default=True,
    help="Don't upload the public key to HQ",
)
@click.option(
    "-o",
    "--organization-name",
    default=None,
    hidden=True,
    help="Deprecated and ignored: the private key is no longer stored in a file",
)
@click.option(
    "--overwrite",
    "overwrite",
    flag_value=True,
    default=False,
    help="Replace the existing private key secret if present",
)
@click.option(
    "--from-file",
    "from_file",
    default=None,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Store an existing PEM-encoded private key instead of generating a new one",
)
@click.option(
    "--replace-organization-key",
    "replace_organization_key",
    flag_value=True,
    default=False,
    help="Allow replacing the public key that HQ already has for your organization. "
    "Other nodes and users of your organization then need the new private key.",
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option("--sandbox/--no-sandbox", "is_sandbox", default=False)
def cli_node_create_private_key(
    name: str,
    config: str,
    system_folders: bool,
    upload: bool,
    organization_name: str | None,
    overwrite: bool,
    from_file: Path | None,
    replace_organization_key: bool,
    context: str | None,
    namespace: str | None,
    is_sandbox: bool,
) -> None:
    """
    Create a private key for the node and store it in a Kubernetes secret

    The key is stored in a Kubernetes secret that is mounted into the node when it
    starts. The secret is kept when the node is stopped and only deleted when the node
    is removed. Use --from-file to store an existing private key instead of generating
    a new one.

    If your organization already has a public key at HQ, use --from-file to store the
    organization's existing private key. Replacing the organization's keypair requires
    --replace-organization-key, as other nodes and users of your organization will no
    longer be able to decrypt data with the old key.
    """
    name, is_sandbox = extract_name_and_is_sandbox(name, is_sandbox)
    if is_sandbox:
        system_folders = False

    # TODO v7+ remove
    if organization_name is not None:
        warning("--organization-name is deprecated and ignored")

    NodeContext.LOGGING_ENABLED = False
    if config:
        name = Path(config).stem
        ctx = NodeContext(
            name,
            system_folders=system_folders,
            is_sandbox=is_sandbox,
            config_file=config,
        )
    elif not name:
        try:
            name = select_configuration_questionnaire(
                InstanceType.NODE, system_folders, is_sandbox
            )
        except FileNotFoundError:
            error("No configurations could be found!")
            sys.exit(1)
    ctx = NodeContext(name, system_folders=system_folders, is_sandbox=is_sandbox)

    pem = None
    if from_file:
        pem = from_file.read_bytes()
        try:
            validate_private_key_pem(pem)
        except (ValueError, TypeError) as e:
            error(f"'{from_file}' does not contain a valid unencrypted private key")
            debug(e)
            sys.exit(1)

    k8s_config = select_k8s_config(context=context, namespace=namespace)
    create_and_store_private_key(
        ctx,
        k8s_config,
        pem=pem,
        overwrite=overwrite,
        upload=upload,
        replace_organization_key=replace_organization_key,
    )
    info("[Done]")


def get_organization_public_key(client: ClientBase) -> str | None:
    """
    Get the public key that HQ has for the organization of the authenticated client.

    Returns
    -------
    str | None
        The organization's public key, or None if it has none
    """
    organization = client.request(f"organization/{client.whoami.organization_id}")
    return organization.get("public_key") or None


def create_and_store_private_key(
    ctx: NodeContext,
    k8s_config: KubernetesConfig,
    pem: bytes | None = None,
    overwrite: bool = False,
    upload: bool = True,
    replace_organization_key: bool = False,
    client: ClientBase | None = None,
) -> None:
    """
    Store the node's private key in a Kubernetes secret and upload its public key.

    If the organization already has a public key at HQ, the stored private key must
    belong to it, unless replace_organization_key is set: replacing the organization's
    keypair breaks decryption for its other nodes and users.

    Parameters
    ----------
    ctx: NodeContext
        Context of the node
    k8s_config: KubernetesConfig
        Kubernetes configuration with the namespace to store the secret in
    pem: bytes | None
        PEM-encoded private key to store. If None, a new key is generated (unless a
        secret already exists and overwrite is False).
    overwrite: bool
        Whether to replace an existing private key secret
    upload: bool
        Whether to check the key against HQ and upload its public key
    replace_organization_key: bool
        Whether replacing the organization's existing public key at HQ is allowed
    client: ClientBase | None
        Authenticated client to use for HQ requests. Created if not given.
    """
    secret_name = private_key_secret_name(ctx)
    try:
        existing = read_private_key_secret(ctx, k8s_config)
    except K8S_ERRORS as e:
        error("Could not read the private key secret from Kubernetes!")
        debug(e)
        sys.exit(1)

    if existing is not None and not overwrite:
        if pem is not None and pem != existing:
            warning(
                f"Private key secret '{secret_name}' already exists; use --overwrite "
                "to replace it with the given key"
            )
        info(f"Keeping the existing private key in secret '{secret_name}'")
        key_to_store = existing
    else:
        key_to_store = pem

    hq_public_key = None
    if upload:
        if client is None:
            client = create_client_and_authenticate(
                ctx, use_sandbox_port=ctx.is_sandbox
            )
        hq_public_key = get_organization_public_key(client)

    if hq_public_key and (
        key_to_store is None or not public_key_matches(key_to_store, hq_public_key)
    ):
        if not replace_organization_key:
            error(
                "Your organization already has a keypair: HQ has a public key for it "
                "that does not match the key you are storing."
            )
            info(
                "Store the organization's existing private key with "
                "'v6 node create-private-key --from-file <path>'. To replace the "
                "organization's keypair instead, use --replace-organization-key."
            )
            sys.exit(1)
        if not q.confirm(
            "This replaces your organization's public key at HQ. Other nodes and "
            "users of your organization will need the new private key, and data "
            "encrypted with the old key can no longer be decrypted. Continue?",
            default=False,
        ).unsafe_ask():
            info("Aborted; nothing was changed")
            sys.exit(0)

    if key_to_store is None:
        info("Generating new private key")
        key_to_store = RSACryptor.create_new_rsa_key_pem()

    if key_to_store != existing:
        try:
            write_private_key_secret(ctx, k8s_config, key_to_store)
        except K8S_ERRORS as e:
            error("Could not store the private key in a Kubernetes secret!")
            debug(e)
            sys.exit(1)

    if not upload:
        warning("Public key not checked against or uploaded to HQ!")
        return

    if hq_public_key and public_key_matches(key_to_store, hq_public_key):
        info("The public key at HQ already belongs to this private key")
        return

    info("Uploading public key to HQ")
    # TODO what happens if the user doesn't have permission to upload key?
    # Does that lead to an exception or not?
    try:
        client.request(
            f"/organization/{client.whoami.organization_id}",
            method="patch",
            json={"public_key": public_key_base64_from_pem(key_to_store)},
        )
    except requests.RequestException as e:
        error("Could not upload the public key!")
        debug(e)
        sys.exit(1)
