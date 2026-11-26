"""
Print the images to scan from docker/maintained-images.toml as a JSON array of
{"image": "<reference>", "category": "<name>-<tag>"} objects, for use as a
GitHub Actions matrix.
"""

import json
import tomllib
from pathlib import Path

MAINTAINED_IMAGES = Path(__file__).parent.parent / "docker/maintained-images.toml"

with MAINTAINED_IMAGES.open("rb") as file:
    config = tomllib.load(file)

targets = [
    {
        "image": f"{spec.get('registry', config['registry'])}/"
        f"{spec.get('image', name)}:{tag}",
        "category": f"{name}-{tag}",
    }
    for name, spec in config.items()
    if isinstance(spec, dict)
    for tag in spec.get("scan-only", []) + spec.get("scan-and-rebuild", [])
]
print(json.dumps(targets))
