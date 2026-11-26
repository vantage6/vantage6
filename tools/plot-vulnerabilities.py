# /// script
# requires-python = ">=3.13"
# dependencies = ["click", "matplotlib"]
# ///
"""
Plot the Trivy findings per image and severity over time, and per image for the
latest scan, from the code scanning analyses that the Container scan workflow
uploads. Requires an authenticated `gh` CLI.

    uv run tools/plot-vulnerabilities.py
"""

import json
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime

import click
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

SEVERITIES = {
    "CRITICAL": "#8b0000",
    "HIGH": "#e4572e",
    "MEDIUM": "#f3a712",
    "LOW": "#f6d55c",
    "UNKNOWN": "#b0b0b0",
}


def gh_api(*args: str) -> str:
    return subprocess.run(
        ["gh", "api", *args], capture_output=True, text=True, check=True
    ).stdout


def fetch_analyses(repo: str, ref: str) -> list[dict]:
    output = gh_api(
        "--paginate",
        "--method",
        "GET",
        f"repos/{repo}/code-scanning/analyses",
        "-f",
        "tool_name=Trivy",
        "-f",
        f"ref={ref}",
        "-f",
        "per_page=100",
        "--jq",
        ".[]",
    )
    return [json.loads(line) for line in output.splitlines()]


def count_severities(repo: str, analysis_id: int) -> Counter:
    sarif = json.loads(
        gh_api(
            "-H",
            "Accept: application/sarif+json",
            f"repos/{repo}/code-scanning/analyses/{analysis_id}",
        )
    )
    counts = Counter()
    for run in sarif["runs"]:
        # Trivy puts the severity in the rule tags
        rule_severity = {
            rule["id"]: next(
                (t for t in rule["properties"]["tags"] if t in SEVERITIES), "UNKNOWN"
            )
            for rule in run["tool"]["driver"]["rules"]
        }
        counts.update(rule_severity[result["ruleId"]] for result in run["results"])
    return counts


def plot_over_time(series: dict, ref: str, output: str) -> None:
    now = datetime.now(UTC)
    fig, axes = plt.subplots(
        len(series),
        1,
        figsize=(10, 3 * len(series)),
        sharex=True,
        squeeze=False,
        layout="constrained",
    )
    for ax, (image, points) in zip(axes[:, 0], sorted(series.items())):
        # a scan's counts hold until the next scan, so extend the last one to now
        points = [*points, (now, points[-1][1])]
        ax.stackplot(
            [date for date, _ in points],
            *([counts[s] for _, counts in points] for s in SEVERITIES),
            labels=SEVERITIES.keys(),
            colors=SEVERITIES.values(),
            step="post",
        )
        ax.set_title(image)
        ax.set_ylabel("Findings")
        ax.grid(alpha=0.3)

    axes[0, 0].legend(loc="upper left", bbox_to_anchor=(1.01, 1), reverse=True)
    locator = mdates.AutoDateLocator()
    axes[-1, 0].xaxis.set_major_locator(locator)
    axes[-1, 0].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    fig.suptitle(f"Trivy findings per image ({ref})")
    fig.savefig(output, dpi=150, bbox_inches="tight")
    click.echo(f"Wrote {output}")


def plot_latest(series: dict, ref: str, output: str) -> None:
    # top to bottom in alphabetical order
    images = sorted(series, reverse=True)
    latest = [series[image][-1][1] for image in images]

    fig, ax = plt.subplots(figsize=(10, 1.5 + 0.3 * len(images)), layout="constrained")
    left = [0] * len(images)
    for severity, color in SEVERITIES.items():
        values = [counts[severity] for counts in latest]
        ax.barh(images, values, left=left, color=color, label=severity)
        left = [a + b for a, b in zip(left, values)]
    for y, total in enumerate(left):
        ax.text(total, y, f" {total}", va="center", fontsize=8)

    ax.set_xlabel("Findings")
    # room for the total labels
    ax.set_xlim(0, max(left) * 1.1)
    ax.grid(axis="x", alpha=0.3)
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1))
    fig.suptitle(f"Trivy findings per image, latest scan ({ref})")
    fig.savefig(output, dpi=150, bbox_inches="tight")
    click.echo(f"Wrote {output}")


@click.command()
@click.option("--repo", default="vantage6/vantage6", help="owner/name")
@click.option("--ref", default="refs/heads/main", help="git ref the scans ran on")
@click.option("--output", default="vulnerabilities.png", help="over time plot")
@click.option(
    "--latest-output",
    default="vulnerabilities-latest.png",
    help="latest scan plot",
)
def plot(repo: str, ref: str, output: str, latest_output: str) -> None:
    analyses = fetch_analyses(repo, ref)
    if not analyses:
        raise click.ClickException(f"No Trivy analyses found for {ref} in {repo}")

    series = defaultdict(list)
    with click.progressbar(analyses, label="Downloading scan reports") as bar:
        for analysis in bar:
            created = datetime.fromisoformat(analysis["created_at"])
            counts = count_severities(repo, analysis["id"])
            series[analysis["category"]].append((created, counts))
    for points in series.values():
        points.sort(key=lambda point: point[0])

    plot_over_time(series, ref, output)
    plot_latest(series, ref, latest_output)


if __name__ == "__main__":
    plot()
