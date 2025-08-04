import re
from pathlib import Path
from typing import List

import click


def find_pyproject_files() -> List[Path]:
    """
    Find all pyproject.toml files in the vantage6 packages.

    Returns
    -------
    List[Path]
        List of paths to pyproject.toml files
    """
    # Find all pyproject.toml files in vantage6 packages
    files = []
    for file_path in Path("../").rglob("pyproject.toml"):
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
        Whether to include a dash between the version and spec (e.g. 5.0.0-1 instead
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
        with open(file_path, "r") as f:
            content = f.read()

        # Update the project version
        content = re.sub(
            r'version = "[\d.]+(a\d+|b\d+|rc\d+)?(\.post\d+)?"',
            f'version = "{new_version}"',
            content,
        )

        # Update all vantage6 dependency versions
        vantage6_packages = [
            "vantage6-common",
            "vantage6-client",
            "vantage6-algorithm-tools",
            "vantage6",
            "vantage6-node",
            "vantage6-backend-common",
            "vantage6-server",
            "vantage6-algorithm-store",
        ]

        for package in vantage6_packages:
            # Match both == and >= dependencies in quoted strings
            pattern = rf'"{package}==[\d.]+(a\d+|b\d+|rc\d+)?(\.post\d+)?"'
            content = re.sub(pattern, f'"{package}=={new_version}"', content)

            pattern = rf'"{package}>=[\d.]+(a\d+|b\d+|rc\d+)?(\.post\d+)?"'
            content = re.sub(pattern, f'"{package}>={new_version}"', content)

        with open(file_path, "w") as f:
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

    # update version label in node-and-server and algorithm store dockerfile
    print("Updating version in Dockerfiles for node, server and algorithm store")
    files = [
        Path("../docker/node-and-server.Dockerfile"),
        Path("../docker/algorithm-store.Dockerfile"),
    ]
    for file in files:
        with open(file, "r") as f:
            content = f.read()
            new_content = re.sub(
                r"(ARG BASE=)(\d+.\d+)", r"\g<1>{}".format(major_minor), content
            )
        with open(file, "w") as f:
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
    # Check if we're running from tools directory or main directory
    package_json = Path("../vantage6-ui/package.json")
    package_lock_json = Path("../vantage6-ui/package-lock.json")

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


def update_uv_lock(version: str, spec: str, build: int) -> None:
    """
    Update version in the uv.lock file

    Parameters
    ----------
    version : str
        The new version to which to update.
    spec : str
        Version spec (final, alpha, beta, candidate)
    build : int
        Build number
    """
    # Check if we're running from tools directory or main directory
    if Path("../uv.lock").exists():
        uv_lock = Path("../uv.lock")
    else:
        uv_lock = Path("uv.lock")

    new_version = build_version_string(version, spec, build)

    # Update the single vantage6 package entry in uv.lock
    update_file_content(
        uv_lock,
        r'name = "vantage6"\nversion = "[\d.]+(a\d+|b\d+|rc\d+)?(\.post\d+)?"',
        f'name = "vantage6"\nversion = "{new_version}"',
        "vantage6 package version",
    )


def update_helm_charts(version: str, spec: str, build: int) -> None:
    """
    Update version in Helm charts

    Parameters
    ----------
    version : str
        The new version to which to update.
    spec : str
        Version spec (final, alpha, beta, candidate)
    build : int
        Build number
    """
    chart_files = [
        Path("../charts/common/Chart.yaml"),
        Path("../charts/node/Chart.yaml"),
        Path("../charts/store/Chart.yaml"),
        Path("../charts/server/Chart.yaml"),
        Path("../charts/auth/Chart.yaml"),
    ]
    new_version = build_version_string(version, spec, build, with_dash=True)

    for chart_file in chart_files:
        print(f"Updating version in {chart_file}")
        with open(chart_file, "r") as f:
            content = f.read()

        # Update appVersion
        content = re.sub(
            r'appVersion: "[\d.]+(-\w+(\.\d+)?)?"',
            f'appVersion: "{new_version}"',
            content,
        )

        # Update version
        content = re.sub(
            r'^version: "[\d.]+(-\w+(\.\d+)?)?"',
            f'version: "{new_version}"',
            content,
            flags=re.MULTILINE,
        )

        # Update common dependency version if it exists
        content = re.sub(
            r'(name: common\n\s+version: )"[\d.]+(-\w+(\.\d+)?)?"',
            f'\\1"{new_version}"',
            content,
        )

        with open(chart_file, "w") as f:
            f.write(content)


@click.command()
@click.option("--spec", default="final", help="final, candidate, beta, alpha")
@click.option("--version", default="0.0.0", help="major.minor.patch")
@click.option("--build", default="0", help="build number for non-final versions")
@click.option("--post", default="0", help=".postN")
def set_version(spec: str, version: str, build: int, post: int) -> None:
    """
    Update version printrmation in all pyproject.toml files and helm charts

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

    update_uv_lock(version, spec, int(build))
    print("uv.lock file updated")

    print("Version update complete!")


if __name__ == "__main__":
    set_version()  # Click handles command line arguments automatically
