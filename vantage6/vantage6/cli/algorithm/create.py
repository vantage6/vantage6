import os
import re
import subprocess
from pathlib import Path

import click
import questionary as q
from copier import run_copy

from vantage6.common import error, warning

from vantage6.cli import __version__
from vantage6.cli.globals import ALGORITHM_TEMPLATE_REPO
from vantage6.cli.utils import info


@click.command()
@click.option(
    "-n", "--name", default=None, type=str, help="Name for your new algorithm"
)
@click.option(
    "-d",
    "--dir",
    "directory",
    default=None,
    type=str,
    help="Directory to put the algorithm into",
)
@click.option(
    "--major-version",
    default=None,
    type=int,
    help="Major version of the algorithm. By default, the current version is used.",
)
def cli_algorithm_create(name: str, directory: str, major_version: int | None) -> dict:
    """Creates a personalized template for a new algorithm

    By answering a number of questions, a template will be created that will
    simplify the creation of a new algorithm. The goal is that the algorithm
    developer only focuses on the algorithm code rather than fitting it to
    the vantage6 infrastructure.

    The created template will contain a Python package with a Dockerfile that
    can be used to build an appropriate Docker image that can be used as a
    vantage6 algorithm.
    """
    latest_tag_of_desired_major_version = None
    if major_version is None:
        major_version = int(__version__.split(".")[0])
    latest_tag_of_desired_major_version = _get_latest_major_tag(major_version)

    try:
        name, directory = _get_user_input(name, directory)
    except KeyboardInterrupt:
        info("Aborted by user!")
        return

    # Create the template. The `unsafe` flag is used to allow running a Python script
    # after creating the template that cleans up some things.
    run_copy(
        ALGORITHM_TEMPLATE_REPO,
        directory,
        data={"algorithm_name": name},
        unsafe=True,
        vcs_ref=latest_tag_of_desired_major_version,
    )
    info("Template created!")
    info(f"You can find your new algorithm in: {directory}")


def _get_user_input(name: str, directory: str) -> None:
    """Get user input for the algorithm creation

    Parameters
    ----------
    name : str
        Name for the new algorithm
    directory : str
        Directory to put the algorithm into
    """
    if not name:
        name = q.text("Name of your new algorithm:").unsafe_ask()

    if not directory:
        default_dir = str(Path(os.getcwd()) / name)
        directory = q.text(
            "Directory to put the algorithm in:", default=default_dir
        ).unsafe_ask()
    return name, directory


def _get_latest_major_tag(major_version: int) -> str | None:
    """Get the latest tag for the given major version"""
    # get the tags from the algorithm template repository
    try:
        tags = _get_algo_template_tags(ALGORITHM_TEMPLATE_REPO)
    except Exception as e:
        error(f"Failed to fetch tags from {ALGORITHM_TEMPLATE_REPO}: {e}")
        warning("Will use latest version instead.")
        return None
    # Filter tags for the given major version (e.g. 5.x.x)
    tags_in_desired_major_version = [
        tag
        for tag in tags
        if tag.startswith(f"{major_version}.")
        and re.match(rf"^{major_version}\.\d+\.\d+", tag)
    ]

    # sort the tags in descending order
    tags_in_desired_major_version.sort(key=lambda s: _gen_sort_key(s), reverse=True)
    return _first_non_prerelease_tag(tags_in_desired_major_version)


def _first_non_prerelease_tag(tags: list[str]) -> str:
    """Return the first non-prerelease tag from a list of tags"""
    for tag in tags:
        patch = tag.split(".")[2]
        try:
            int(patch)
            return tag
        except ValueError:
            continue
    # no non-prerelease tag found - return first in the list (sorted in descending
    # order)
    return tags[0] if tags else None


def _gen_sort_key(tag: str) -> list[int]:
    """Generate a sort key for a tag"""
    major = int(tag.split(".")[0])
    minor = int(tag.split(".")[1])
    # Note: patch is not cast to int for sorting, because it may contain
    # alpha/beta/rc suffixes
    # TODO this will go wrong in sorting 1.2.13a1 vs 1.2.3a1, but we don't care
    # about that for now, as it is unlikely that we have 10+ patch releases
    # for the algorithm template repository
    patch = tag.split(".")[2]
    return [major, minor, patch]


def _get_algo_template_tags(repo_url: str) -> list[str]:
    """Get all tags from a git repository

    Parameters
    ----------
    repo_url : str
        Repository URL in format like "gh:owner/repo.git" or full git URL

    Returns
    -------
    list[str]
        List of tag names (without refs/tags/ prefix)
    """
    # Convert copier format (gh:owner/repo.git) to git URL
    if repo_url.startswith("gh:"):
        # Format: gh:owner/repo.git -> https://github.com/owner/repo.git
        repo_path = repo_url[3:].rstrip(".git")
        git_url = f"https://github.com/{repo_path}.git"
    else:
        git_url = repo_url

    try:
        # Use git ls-remote to fetch tags without cloning
        result = subprocess.run(
            ["git", "ls-remote", "--tags", git_url],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )

        # Parse output: lines look like "hash\trefs/tags/v1.0.0"
        tags = []
        for line in result.stdout.strip().split("\n"):
            if line:
                # Extract tag name from "refs/tags/tagname"
                match = re.search(r"refs/tags/(.+)", line)
                if match:
                    tag = match.group(1)
                    # Filter out ^{} suffix that git adds for annotated tags
                    if not tag.endswith("^{}"):
                        tags.append(tag)

        return sorted(tags)
    except subprocess.CalledProcessError as e:
        info(f"Failed to fetch tags from {git_url}: {e}")
        return []
    except subprocess.TimeoutExpired:
        info(f"Timeout while fetching tags from {git_url}")
        return []
    except FileNotFoundError:
        info("git command not found. Please install git to fetch repository tags.")
        return []
