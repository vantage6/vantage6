"""
Development helpers to connect and seed the local algorithm store.
"""

import re
from urllib.parse import urlparse

import requests

from vantage6.client import Client
from vantage6.common import info, warning

COMMUNITY_REPO = "vantage6/vantage6-community-algorithms"
COMMUNITY_GITMODULES_URL = (
    f"https://raw.githubusercontent.com/{COMMUNITY_REPO}/main/.gitmodules"
)
EXTRA_ALGORITHM_REPOS = [
    "vantage6/v6-average-py",
]


def _normalize_path(path: str) -> str:
    path = path.strip()
    if not path:
        return ""
    if not path.startswith("/"):
        path = f"/{path}"
    return path.rstrip("/")


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


def _compose_store_api_url(store_url: str, api_path: str) -> str:
    store_url = _normalize_url(store_url)
    api_path = _normalize_path(api_path)
    if api_path and store_url.endswith(api_path):
        return store_url
    return f"{store_url}{api_path}"


def _extract_github_repo_slug(url: str) -> str | None:
    """
    Convert a GitHub submodule URL to a "<owner>/<repo>" slug.
    """
    if url.startswith("git@github.com:"):
        slug = url.replace("git@github.com:", "").removesuffix(".git")
        return slug

    parsed = urlparse(url)
    if parsed.netloc != "github.com":
        return None
    return parsed.path.strip("/").removesuffix(".git")


def _parse_submodule_repo_slugs(gitmodules_text: str) -> list[str]:
    """
    Parse repo slugs from a .gitmodules file.
    """
    urls = re.findall(r"^\s*url\s*=\s*(.+)\s*$", gitmodules_text, flags=re.MULTILINE)
    repo_slugs = []
    for url in urls:
        slug = _extract_github_repo_slug(url.strip())
        if slug:
            repo_slugs.append(slug)
    return repo_slugs


def _download_community_algorithm_metadata() -> list[tuple[str, dict]]:
    """
    Download algorithm metadata JSON from each community algorithm submodule.
    """
    info(f"Downloading submodule list from {COMMUNITY_REPO}")
    response = requests.get(COMMUNITY_GITMODULES_URL, timeout=10)
    response.raise_for_status()
    repo_slugs = _parse_submodule_repo_slugs(response.text)
    repo_slugs.extend(EXTRA_ALGORITHM_REPOS)
    # Keep order stable, deduplicate repos that are already in submodules.
    repo_slugs = list(dict.fromkeys(repo_slugs))
    info(f"Found {len(repo_slugs)} community algorithm repositories")

    metadata: list[tuple[str, dict]] = []
    for repo_slug in repo_slugs:
        metadata_url = (
            f"https://raw.githubusercontent.com/{repo_slug}/main/algorithm_store.json"
        )
        if "v6-average-py" in repo_slug:
            # average repo still has master branch instead of main
            metadata_url = metadata_url.replace("main", "master")
        try:
            info(f"Downloading metadata from {repo_slug}")
            repo_response = requests.get(metadata_url, timeout=10)
            repo_response.raise_for_status()
            raw = repo_response.json()
            if isinstance(raw, list):
                for entry in raw:
                    if isinstance(entry, dict):
                        metadata.append((repo_slug, entry))
            elif isinstance(raw, dict):
                metadata.append((repo_slug, raw))
        except (requests.RequestException, ValueError) as exc:
            warning(
                f"Skipping {repo_slug}: could not load algorithm_store.json ({exc})"
            )
    return metadata


def _normalize_algorithm_metadata(repo_slug: str, metadata: dict) -> dict:
    """
    Normalize algorithm metadata to the expected create payload.
    """
    repo_name = repo_slug.split("/")[-1]
    algorithm_name = (
        metadata.get("name")
        or repo_name.removeprefix("v6-").removesuffix("-py").replace("-", " ").title()
    )
    image_name = metadata.get("image")
    if not image_name:
        image_suffix = repo_name.removeprefix("v6-").removesuffix("-py")
        image_name = f"ghcr.io/vantage6/algorithm/{image_suffix}:latest"
    elif ":" not in image_name and "@sha256:" not in image_name:
        image_name = f"{image_name}:latest"

    return {
        "name": algorithm_name,
        "description": metadata.get(
            "description", f"{algorithm_name} algorithm from community repository"
        ),
        "image": image_name,
        "partitioning": metadata.get("partitioning", "horizontal"),
        "vantage6_version": metadata.get("vantage6_version", "5.0.0"),
        "code_url": metadata.get("code_url", f"https://github.com/{repo_slug}"),
        "documentation_url": metadata.get("documentation_url"),
        "functions": metadata.get("functions", []),
    }


def _register_community_algorithms(client: Client) -> None:
    """
    Seed local demo algorithms via the server API.
    """
    try:
        all_metadata = _download_community_algorithm_metadata()
    except requests.RequestException as exc:
        warning(f"Could not download community algorithm metadata: {exc}")
        return

    try:
        existing_names = {a["name"] for a in client.algorithm.list().get("data", [])}
    except Exception as exc:
        warning(
            "Could not list existing algorithms in local store. "
            f"Continuing with empty baseline. Details: {exc}"
        )
        existing_names = set()
    created_count = 0

    for repo_slug, metadata in all_metadata:
        payload = _normalize_algorithm_metadata(repo_slug, metadata)
        if payload["name"] in existing_names:
            info(f"Skipping existing algorithm '{payload['name']}'")
            continue
        info(f"Creating algorithm '{payload['name']}' from {payload['code_url']}")
        client.algorithm.create(
            name=payload["name"],
            description=payload["description"],
            image=payload["image"],
            partitioning=payload["partitioning"],
            vantage6_version=payload["vantage6_version"],
            code_url=payload["code_url"],
            functions=payload["functions"],
            documentation_url=payload["documentation_url"],
        )
        created_count += 1

    info(f"Seeded {created_count} algorithms from community metadata")


def connect_and_seed_local_store(
    client: Client, local_store_url: str, store_api_path: str
) -> None:
    """
    Couple a local store to server and seed demo algorithms.
    """
    normalized_store_url = _normalize_url(local_store_url)
    normalized_api_url = _compose_store_api_url(normalized_store_url, store_api_path)
    existing_stores = client.store.list().get("data", [])
    store = next(
        (
            s
            for s in existing_stores
            if _normalize_url(s["url"]) in [normalized_store_url, normalized_api_url]
        ),
        None,
    )

    if store is None:
        info("Linking local algorithm store to server")
        # Server probes {algorithm_store_url}/vantage6-server; the store serves
        # that under the API prefix (default /api). URL must include that prefix.
        store = client.store.create(
            algorithm_store_url=normalized_api_url,
            name="local store",
            all_collaborations=True,
            force=True,
        )
    else:
        info(f"Local algorithm store already linked: {store['url']}")

    client.store.set(store["id"])
    client.store.url = _compose_store_api_url(store["url"], store_api_path)
    info(f"Using algorithm store API endpoint {client.store.url}")
    _register_community_algorithms(client)
