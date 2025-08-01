import re
from pathlib import Path

import click


# from vantage6.common import info
def info(msg: str):
    """
    Print a message to the console.

    Parameters
    ----------
    msg : str
    """
    print(msg)


# pattern to use in the regex to update version
pattern = (
    r"(version_info\s*=\s*\()(\s*\d+,\s*\d+,\s*\d+,)(\s*)(\"\w*\")"
    r"(,\s*__build__)(,\s*)(\d+)(\))"
)


def update_version_spec(spec: str) -> None:
    """
    Update version spec in all instances of _version.py

    Parameters
    ----------
    spec : str
        The new version spec to which to update.

    Raises
    ------
    AssertionError
        If the spec is not one of the following: final, beta, alpha, candidate
    """
    assert spec in ("final", "beta", "alpha", "candidate")
    # find all _version.py files
    files = [
        file_ for file_ in Path("../").rglob("_version.py") if "build" not in str(file_)
    ]
    info(f"found files={files}")
    # update spec in all files
    for file in files:
        info(f"File: {file}")
        info(f"Updating spec to: {spec}")
        with open(file, "r") as f:
            content = f.read()
            new_content = re.sub(
                pattern, r'\1\2\g<3>"{}"\5\6\7\8'.format(spec), content
            )

        info("Writing to file")
        with open(file, "w") as f:
            f.write(new_content)


def update_version(version: str) -> None:
    """
    Update version in all instances of _version.py

    Parameters
    ----------
    version : str
        The new version to which to update.

    Raises
    ------
    AssertionError
        If the version is not in the format of major.minor.patch
    """
    print(version)
    assert re.match(r"\d+.\d+.\d+", version)
    # find all _version.py files
    files = [
        file_ for file_ in Path("../").rglob("_version.py") if "build" not in str(file_)
    ]
    # update version in all files
    for file in files:
        info(f"File: {file}")
        info(f"Updating version to {version}")
        major, minor, patch = version.split(".")
        with open(file, "r") as f:
            content = f.read()
            new_content = re.sub(
                pattern,
                r"\g<1>{}, {}, {},\3\4\5\6\7\8".format(major, minor, patch),
                content,
            )

        info("Writing to file")
        with open(file, "w") as f:
            f.write(new_content)


def update_build(build: int) -> None:
    """Update build number in all instances of __build__

    Parameters
    ----------
    build : int
        The new build number to which to update.
    """
    files = Path("../").rglob("__build__")
    info(f"Updating build number to {build}")
    for file in files:
        info(f"File: {file}")
        with open(file, "w") as f:
            f.write(build)


def update_post(post: str) -> None:
    """Update post release version in all instances of _version.py

    Parameters
    ----------
    post : str
        The new post release version to which to update.
    """
    files = [
        file_ for file_ in Path("../").rglob("_version.py") if "build" not in str(file_)
    ]
    info(f"Setting post-release version to: {post}")
    for file_ in files:
        info(f"File: {file_}")
        with open(file_, "r") as f:
            content = f.read()
            new_content = re.sub(pattern, r"\1\2\3\4\5\g<6>{}\8".format(post), content)

        info("Writing to file")
        with open(file_, "w") as f:
            f.write(new_content)


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
    info("Updating version in Dockerfiles for node, server and algorithm store")
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


def update_helm_charts(version: str, spec: str, build: int) -> None:
    """
    Update version in Helm charts

    Parameters
    ----------
    version : str
        The new version to which to update.
    """
    chart_files = [
        Path("../charts/common/Chart.yaml"),
        Path("../charts/node/Chart.yaml"),
        Path("../charts/store/Chart.yaml"),
        Path("../charts/server/Chart.yaml"),
        Path("../charts/auth/Chart.yaml"),
    ]
    if spec == "final":
        new_version = version
    else:
        if spec == "candidate":
            spec_ = "rc"
        elif spec == "beta":
            spec_ = "b"
        elif spec == "alpha":
            spec_ = "a"
        else:
            raise ValueError(f"Invalid spec: {spec}")

        new_version = f"{version}-{spec_}.{build}"

    for chart_file in chart_files:
        info(f"Updating version in {chart_file}")
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
    Update version information in all instances of _version.py and __build__

    Parameters
    ----------
    spec : str
        The new version spec to which to update.
    version : str
        The new version to which to update.
    build : int
        The new build number to which to update.
    post : str
        The new post release version to which to update.
    """
    update_version_spec(spec)
    info("Version specs updated")

    update_version(version)
    info("Version numbers updated")

    update_build(str(build))
    info("Build number updated")

    update_post(str(post))
    info("Post release version set")

    update_version_docker_files(version)
    info("Docker files updated")

    update_helm_charts(version, spec, build)
    info("Helm charts updated")


if __name__ == "__main__":
    set_version()
