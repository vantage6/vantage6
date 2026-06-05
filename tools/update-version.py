import re
from datetime import datetime
from pathlib import Path
from typing import List

import click

VANTAGE6_PACKAGES = [
    "vantage6-common",
    "vantage6-client",
    "vantage6-algorithm-tools",
    "vantage6",
    "vantage6-node",
    "vantage6-backend-common",
    "vantage6-hq",
    "vantage6-algorithm-store",
]

# Workspace members listed in uv.lock [[package]] entries.
UV_LOCK_PACKAGES = [*VANTAGE6_PACKAGES, "vantage6-base"]

# Pattern to match version in uv.lock [[package]] entries
LOCK_VERSION_PATTERN = r"[\d.]+(?:a\d+|b\d+|rc\d+)?(?:\.post\d+)?"

# Pattern to match version in pyproject.toml [project] version field
PROJECT_VERSION_PATTERN = re.compile(
    r'(?<=^version = ")[\d.]+(?:a\d+|b\d+|rc\d+)?(?:\.post\d+)?(?=")',
    re.MULTILINE,
)
# Pattern to match version in pyproject.toml dependencies
PACKAGE_PIN_PATTERN = re.compile(
    r'"(vantage6(?:-[a-z-]+)?)(==|>=)([\d.]+(?:a\d+|b\d+|rc\d+)?(?:\.post\d+)?)"'
)

# Matches Helm chart / Chart.lock version strings (e.g. 5.0.1, 5.0.0-rc9)
HELM_CHART_VERSION_PATTERN = r"[\d.]+(-\w+(\.\d+)?)?(\.post\d+)?"


def repo_root() -> Path:
    """Return the repository root (parent of the tools/ directory)."""
    return Path(__file__).resolve().parent.parent


def find_pyproject_files() -> List[Path]:
    """
    Find all pyproject.toml files in the vantage6 packages.

    Returns
    -------
    List[Path]
        List of paths to pyproject.toml files
    """
    files = []
    for file_path in repo_root().rglob("pyproject.toml"):
        # Skip docs, node_modules, .venv and other non-package pyproject.toml files
        if (
            "docs" not in str(file_path)
            and "node_modules" not in str(file_path)
            and ".venv" not in str(file_path)
        ):
            files.append(file_path)
    return files


def build_version_string(
    version: str, spec: str, build: int, post: int = 0, with_dash: bool = False
) -> str:
    """
    Build the complete version string based on components.

    Parameters
    ----------
    version : str
        Version in format major.minor.patch
    spec : str
        Version spec (final, alpha, beta, candidate)
    build : int
        Build number
    post : int
        Post release number
    with_dash : bool
        Whether to include a dash between the version and spec (e.g. 5.0.0-a1 instead
        of 5.0.0a1)

    Returns
    -------
    str
        Complete version string
    """
    if spec == "final":
        version_str = version
    else:
        if spec == "candidate":
            spec_ = "rc"
        elif spec == "beta":
            spec_ = "b"
        elif spec == "alpha":
            spec_ = "a"
        else:
            raise ValueError(f"Invalid spec: {spec}")

        if with_dash:
            version_str = f"{version}-{spec_}{build}"
        else:
            version_str = f"{version}{spec_}{build}"

    if post > 0:
        version_str = f"{version_str}.post{post}"

    return version_str


def update_file_content(
    file_path: Path, pattern: str, replacement: str, description: str = ""
) -> None:
    """
    Update file content using regex pattern replacement.

    Parameters
    ----------
    file_path : Path
        Path to the file to update
    pattern : str
        Regex pattern to match
    replacement : str
        Replacement string
    description : str
        Description for logging
    """
    if not file_path.exists():
        return

    if description:
        print(f"Updating {description} in {file_path}")

    with open(file_path, "r") as f:
        content = f.read()

    content = re.sub(pattern, replacement, content)

    with open(file_path, "w") as f:
        f.write(content)


def _replace_project_version(content: str, new_version: str) -> str:
    """Update only the [project] version field (first match in each pyproject.toml)."""
    return PROJECT_VERSION_PATTERN.sub(new_version, content, count=1)


def _replace_package_pins(content: str, new_version: str) -> str:
    """
    Update pinned inter-package dependencies (== / >=).

    The root pyproject.toml uses uv workspace sources without version pins; those
    entries are left unchanged.
    """

    def replacer(match: re.Match) -> str:
        package, operator, _old_version = match.groups()
        if package not in VANTAGE6_PACKAGES:
            return match.group(0)
        return f'"{package}{operator}{new_version}"'

    return PACKAGE_PIN_PATTERN.sub(replacer, content)


def update_pyproject_versions(version: str, spec: str, build: int, post: int) -> None:
    """
    Update version in all pyproject.toml files.

    Parameters
    ----------
    version : str
        Version in format major.minor.patch
    spec : str
        Version spec (final, alpha, beta, candidate)
    build : int
        Build number
    post : int
        Post release number
    """
    new_version = build_version_string(version, spec, build, post)
    files = find_pyproject_files()

    print(f"Updating versions to: {new_version}")
    print(f"Found {len(files)} pyproject.toml files")

    for file_path in files:
        print(f"Updating: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        content = _replace_project_version(content, new_version)
        content = _replace_package_pins(content, new_version)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)


def update_version_docker_files(version: str) -> None:
    """
    Update version in relevant Dockerfiles

    Parameters
    ----------
    version : str
        The new version to which to update.
    """
    major_minor = ".".join(version.split(".")[:2])

    # update version label in node-and-hq and algorithm store dockerfile
    print("Updating version in Dockerfiles for node, HQ and algorithm store")
    root = repo_root()
    files = [
        root / "docker/node-and-hq.Dockerfile",
        root / "docker/algorithm-store.Dockerfile",
    ]
    for file in files:
        if not file.exists():
            raise Exception(f"Skipping missing Dockerfile: {file}")
        with open(file, "r", encoding="utf-8") as f:
            content = f.read()
            new_content = re.sub(
                r"(ARG BASE=)(\d+.\d+)", r"\g<1>{}".format(major_minor), content
            )
        with open(file, "w", encoding="utf-8") as f:
            f.write(new_content)


def update_ui_package(version: str, spec: str, build: int) -> None:
    """
    Update version in the UI package.json file

    Parameters
    ----------
    version : str
        The new version to which to update.
    spec : str
        Version spec (final, alpha, beta, candidate)
    build : int
        Build number
    """
    package_json = repo_root() / "vantage6-ui/package.json"
    package_lock_json = repo_root() / "vantage6-ui/package-lock.json"

    new_version = build_version_string(version, spec, build, with_dash=True)

    # Update package.json
    update_file_content(
        package_json,
        r'"version": "[\d.]+(-[a-z]+\d+)?(\.post\d+)?"',
        f'"version": "{new_version}"',
        "version",
    )

    # Update package-lock.json - only the main package version, not all dependencies
    if package_lock_json.exists():
        print(f"Updating version in {package_lock_json}")
        with open(package_lock_json, "r") as f:
            content = f.read()

        # Update only the main package version (after "name": "vantage6-UI")
        # This regex matches version after the main package name, not all version
        # entries
        content = re.sub(
            r'("name": "vantage6-UI",\s*)"version": '
            r'"[\d.]+(-[a-z]+\d+)?(\.post\d+)?"',
            f'\\1"version": "{new_version}"',
            content,
        )

        with open(package_lock_json, "w") as f:
            f.write(content)


def update_uv_lock(version: str, spec: str, build: int, post: int) -> None:
    """
    Update workspace package versions in uv.lock without running ``uv lock``.

    Only the ``[[package]]`` version fields for vantage6 workspace members are
    updated. Dependency resolution is unchanged; run ``make lock`` separately
    if you need a full lock refresh.
    """
    uv_lock = repo_root() / "uv.lock"
    if not uv_lock.exists():
        raise Exception(f"Skipping uv.lock update: {uv_lock} not found")

    new_version = build_version_string(version, spec, build, post)
    print(f"Updating workspace package versions in {uv_lock}")

    with open(uv_lock, "r", encoding="utf-8") as f:
        content = f.read()

    for package in UV_LOCK_PACKAGES:
        pattern = (
            rf'(name = "{re.escape(package)}"\nversion = ")'
            rf"{LOCK_VERSION_PATTERN}"
            rf'(")'
        )
        content, count = re.subn(pattern, rf"\g<1>{new_version}\g<2>", content)
        if count:
            print(f"  {package}: {count} version(s) updated")

    with open(uv_lock, "w", encoding="utf-8") as f:
        f.write(content)


def update_helm_charts(version: str, spec: str, build: int) -> None:
    """
    Update version in Helm Chart.yaml and Chart.lock files.

    Parameters
    ----------
    version : str
        The new version to which to update.
    spec : str
        Version spec (final, alpha, beta, candidate)
    build : int
        Build number
    """
    root = repo_root()
    chart_files = [
        root / "charts/common/Chart.yaml",
        root / "charts/node/Chart.yaml",
        root / "charts/store/Chart.yaml",
        root / "charts/hq/Chart.yaml",
        root / "charts/auth/Chart.yaml",
        root / "charts/hub/Chart.yaml",
    ]
    new_version = build_version_string(version, spec, build, with_dash=True)
    helm_version_pattern = HELM_CHART_VERSION_PATTERN

    for chart_file in chart_files:
        if not chart_file.exists():
            raise Exception(f"Skipping missing chart: {chart_file}")
        print(f"Updating version in {chart_file}")
        with open(chart_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Update appVersion
        content = re.sub(
            rf'appVersion: "{helm_version_pattern}"',
            f'appVersion: "{new_version}"',
            content,
        )

        # Update version
        content = re.sub(
            rf'^version: "{helm_version_pattern}"',
            f'version: "{new_version}"',
            content,
            flags=re.MULTILINE,
        )

        # Update subchart dependency versions in Chart.yaml
        content = re.sub(
            rf'(name: (common|hq|auth|store|node)\n\s+version: )"'
            rf"{helm_version_pattern}"
            rf'"',
            f'\\1"{new_version}"',
            content,
        )

        with open(chart_file, "w", encoding="utf-8") as f:
            f.write(content)

    generated = datetime.now().astimezone().isoformat()
    for lock_file in sorted((root / "charts").rglob("Chart.lock")):
        print(f"Updating dependency versions in {lock_file}")
        with open(lock_file, "r", encoding="utf-8") as f:
            content = f.read()

        content = re.sub(
            rf'(^  version: )"?{helm_version_pattern}"?',
            rf"\g<1>{new_version}",
            content,
            flags=re.MULTILINE,
        )
        content = re.sub(
            r'^generated: ".*"',
            f'generated: "{generated}"',
            content,
            flags=re.MULTILINE,
        )

        with open(lock_file, "w", encoding="utf-8") as f:
            f.write(content)


@click.command()
@click.option("--spec", default="final", help="final, candidate, beta, alpha")
@click.option("--version", default="0.0.0", help="major.minor.patch")
@click.option("--build", default="0", help="build number for non-final versions")
@click.option("--post", default="0", help=".postN")
def set_version(spec: str, version: str, build: int, post: int) -> None:
    """
    Update version information in all pyproject.toml files and helm charts

    Parameters
    ----------
    spec : str
        The new version spec to which to update.
    version : str
        The new version to which to update.
    build : int
        The new build number to which to update.
    post : int
        The new post release version to which to update.
    """
    # Validate inputs
    assert spec in ("final", "beta", "alpha", "candidate"), f"Invalid spec: {spec}"
    assert re.match(r"\d+.\d+.\d+", version), f"Invalid version format: {version}"
    assert int(build) >= 0, f"Build number must be non-negative: {build}"
    assert int(post) >= 0, f"Post number must be non-negative: {post}"

    print("Updating versions:")
    print(f"  Version: {version}")
    print(f"  Spec: {spec}")
    print(f"  Build: {build}")
    print(f"  Post: {post}")

    update_pyproject_versions(version, spec, int(build), int(post))
    print("Pyproject.toml files updated")

    update_version_docker_files(version)
    print("Docker files updated")

    update_helm_charts(version, spec, int(build))
    print("Helm charts updated")

    update_ui_package(version, spec, int(build))
    print("UI package files updated")

    update_uv_lock(version, spec, int(build), int(post))
    print("uv.lock workspace package versions updated")

    print("Version update complete!")


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    set_version()  # Click handles command line arguments automatically
