"""
Config-driven seeding of algorithms during store database initialization.

Reads ``link_algorithms`` from the store configuration (top-level YAML next to
``root_user``, ``policies``, etc.).
"""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import requests
from marshmallow import ValidationError

from vantage6.common import logger_name

from vantage6.algorithm.store import db
from vantage6.algorithm.store.algorithm_create import (
    create_algorithm_from_validated_data,
    resolve_image_digest,
)
from vantage6.algorithm.store.model.algorithm import Algorithm as db_Algorithm
from vantage6.algorithm.store.resource.schema.input_schema import (
    AlgorithmInputSchema,
)

algorithm_input_post_schema = AlgorithmInputSchema()

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

COMMUNITY_REPO = "vantage6/vantage6-community-algorithms"
COMMUNITY_GITMODULES_URL = (
    f"https://raw.githubusercontent.com/{COMMUNITY_REPO}/main/.gitmodules"
)

BASICS_REPO_SLUG = "vantage6/v6-session-basics"
DEMO_REPO_SLUG = "vantage6/v6-average-py"


def _parse_link_algorithms_config(config: dict) -> dict:
    """Parse the link_algorithms configuration."""
    raw = config.get("link_algorithms", {})
    return {
        "list": list(raw.get("list") or []),
        "community": bool(raw.get("community", False)),
        "basics": bool(raw.get("basics", False)),
        "demo": bool(raw.get("demo", False)),
    }


def _normalize_url(url: str) -> str:
    """Normalize a URL."""
    u = url.strip()
    if not u:
        return u
    if "://" not in u:
        u = f"https://{u}"
    return u.rstrip("/")


def _extract_github_repo_slug(url: str) -> str | None:
    """Extract the GitHub repository slug from a URL.

    Example:
    >>> _extract_github_repo_slug("git@github.com:vantage6/v6-average-py.git")
    "vantage6/v6-average-py"
    >>> _extract_github_repo_slug("https://github.com/vantage6/v6-average-py.git")
    "vantage6/v6-average-py"
    """
    if url.startswith("git@github.com:"):
        return url.replace("git@github.com:", "").removesuffix(".git")
    parsed = urlparse(url)
    if parsed.netloc != "github.com":
        return None
    return parsed.path.strip("/").removesuffix(".git")


def _parse_submodule_repo_slugs(gitmodules_text: str) -> list[str]:
    """Parse the submodule repository slugs from the .gitmodules file."""
    urls = re.findall(r"^\s*url\s*=\s*(.+)\s*$", gitmodules_text, flags=re.MULTILINE)
    repo_slugs: list[str] = []
    for url in urls:
        slug = _extract_github_repo_slug(url.strip())
        if slug:
            repo_slugs.append(slug)
    return repo_slugs


def _algorithm_store_json_url(repo_slug: str) -> str:
    """Get the URL of the JSON file that contains the algorithm store metadata."""
    url = f"https://raw.githubusercontent.com/{repo_slug}/main/algorithm_store.json"
    # average repo uses master branch
    # TODO we should make the branch configurable
    if "v6-average-py" in repo_slug:
        return url.replace("main", "master")
    return url


def _load_linked_algorithm_metadata(
    url: str, *, repo_slug: str | None = None
) -> list[tuple[str | None, dict]]:
    """
    GET ``url`` and parse a single JSON object (one algorithm's metadata).

    ``repo_slug`` is attached to the result for :func:`_normalize_algorithm_metadata`
    (defaults from GitHub repo); use ``None`` for arbitrary URLs in ``link_algorithms.list``.
    """
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        raw = resp.json()
    except (requests.RequestException, ValueError) as exc:
        ctx = f"repo {repo_slug} ({url})" if repo_slug else url
        log.warning("link_algorithms: could not load %s: %s", ctx, exc)
        return []
    if not isinstance(raw, dict):
        ctx = f"{url} (repo {repo_slug})" if repo_slug else url
        log.warning(
            "link_algorithms: expected a JSON object at %s, got %s",
            ctx,
            type(raw).__name__,
        )
        return []
    return [(repo_slug, raw)]


def _fetch_json_metadata_entries(repo_slug: str) -> list[tuple[str | None, dict]]:
    """Fetch ``algorithm_store.json`` for a GitHub repo (same JSON contract as list URLs)."""
    return _load_linked_algorithm_metadata(
        _algorithm_store_json_url(repo_slug), repo_slug=repo_slug
    )


def _metadata_from_list_url(url: str) -> list[tuple[str | None, dict]]:
    """Fetch one algorithm from a URL in ``link_algorithms.list`` (single JSON object)."""
    return _load_linked_algorithm_metadata(_normalize_url(url), repo_slug=None)


def _download_community_metadata() -> list[tuple[str | None, dict]]:
    try:
        response = requests.get(COMMUNITY_GITMODULES_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        log.warning(
            "link_algorithms: could not download community .gitmodules: %s", exc
        )
        return []
    repo_slugs = _parse_submodule_repo_slugs(response.text)
    repo_slugs = list(dict.fromkeys(repo_slugs))
    entries: list[tuple[str, dict]] = []
    for slug in repo_slugs:
        entries.extend(_fetch_json_metadata_entries(slug))
    return entries


def _normalize_algorithm_metadata(repo_slug: str | None, metadata: dict) -> dict:
    """Build a dict suitable for :class:`AlgorithmInputSchema`."""
    algorithm_name = metadata.get("name")
    image_name = metadata.get("image")
    if not image_name:
        log.warning(
            "link_algorithms: metadata must include 'image'. Skipping algorithm '%s'",
            algorithm_name,
        )
        return {}
    elif ":" not in image_name:
        image_name = f"{image_name}:latest"

    out = {
        "name": algorithm_name,
        "description": metadata.get(
            "description",
            f"{algorithm_name} algorithm from community repository",
        ),
        "image": image_name,
        "partitioning": metadata.get("partitioning"),
        "vantage6_version": metadata.get("vantage6_version"),
        "code_url": (
            metadata.get("code_url")
            or (f"https://github.com/{repo_slug}" if repo_slug else "")
        ),
        "functions": metadata.get("functions", []),
    }
    doc_url = metadata.get("documentation_url")
    if doc_url is not None:
        out["documentation_url"] = doc_url
    return out


def link_algorithms_from_config(config: dict) -> None:
    """
    Create algorithms from ``link_algorithms`` configuration.

    Idempotent: skips algorithms whose name already exists in the database.
    """
    opts = _parse_link_algorithms_config(config)
    if (
        not opts["list"]
        and not opts["community"]
        and not opts["basics"]
        and not opts["demo"]
    ):
        log.info("link_algorithms: disabled (empty list, all presets false)")
        return

    root_username = (config.get("root_user") or {}).get("username")
    if root_username:
        developer = db.User.get_by_username(root_username)
    else:
        developer = db.User.get_first_user()
    if not developer:
        log.warning(
            "link_algorithms: No users found; skipping seeding",
            root_username,
        )
        return

    existing_names = {a.name for a in db_Algorithm.get()}

    ordered: list[tuple[str | None, dict]] = []
    for url in opts["list"]:
        ordered.extend(_metadata_from_list_url(url))
    if opts["basics"]:
        ordered.extend(_fetch_json_metadata_entries(BASICS_REPO_SLUG))
    if opts["demo"]:
        ordered.extend(_fetch_json_metadata_entries(DEMO_REPO_SLUG))
    if opts["community"]:
        ordered.extend(_download_community_metadata())

    seen: set[str] = set()
    created = 0
    for repo_slug, metadata in ordered:
        try:
            payload = _normalize_algorithm_metadata(repo_slug, metadata)
        except ValueError as exc:
            log.warning("link_algorithms: skip invalid metadata: %s", exc)
            continue
        name = payload["name"]
        if name in existing_names or name in seen:
            log.debug("link_algorithms: skip existing or duplicate '%s'", name)
            continue
        seen.add(name)

        try:
            data = algorithm_input_post_schema.load(payload)
        except ValidationError as exc:
            log.warning(
                "link_algorithms: validation failed for '%s': %s", name, exc.messages
            )
            continue

        try:
            image, digest = resolve_image_digest(data["image"], config)
        except ValueError as exc:
            log.warning("link_algorithms: invalid image for '%s': %s", name, exc)
            continue
        if digest is None:
            log.warning(
                "link_algorithms: could not resolve digest for '%s' image %s",
                name,
                data["image"],
            )
            continue

        try:
            create_algorithm_from_validated_data(
                data,
                developer.id,
                config,
                resolved_image=image,
                digest=digest,
                auto_approve=True,
            )
        except Exception:
            log.exception("link_algorithms: failed to create algorithm '%s'", name)
            continue

        existing_names.add(name)
        created += 1
        log.info("link_algorithms: created algorithm '%s'", name)

    log.info("link_algorithms: finished (%s new algorithm(s))", created)
