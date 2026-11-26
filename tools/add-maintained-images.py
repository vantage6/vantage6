# /// script
# requires-python = ">=3.13"
# dependencies = ["tomlkit"]
# ///
"""
Add published image references to the scan-only list of their table in
docker/maintained-images.toml, when that table exists and does not list the tag
yet. Prints a Markdown summary for the pull request.

    uv run tools/add-maintained-images.py ghcr.io/vantage6/infrastructure/hq:5.1.1 ...
"""

import sys
from pathlib import Path

import tomlkit

MAINTAINED_IMAGES = Path(__file__).parent.parent / "docker/maintained-images.toml"

config = tomlkit.parse(MAINTAINED_IMAGES.read_text())
tables = {
    f"{spec.get('registry', config['registry'])}/{spec.get('image', name)}": spec
    for name, spec in config.items()
    if isinstance(spec, dict)
}

added, listed, not_maintained = [], [], []
for reference in sys.argv[1:]:
    repository, tag = reference.rsplit(":", 1)
    spec = tables.get(repository)
    if spec is None:
        not_maintained.append(reference)
    elif tag in spec.get("scan-only", []) + spec.get("scan-and-rebuild", []):
        listed.append(reference)
    else:
        if "scan-only" not in spec:
            spec["scan-only"] = []
        spec["scan-only"].append(tag)
        added.append(reference)

MAINTAINED_IMAGES.write_text(tomlkit.dumps(config))

for title, references in [
    ("Added to `scan-only`", added),
    ("Already listed", listed),
    ("Published but not maintained (no table in the file)", not_maintained),
]:
    if references:
        print(f"**{title}**\n")
        print("\n".join(f"- `{reference}`" for reference in references), end="\n\n")
