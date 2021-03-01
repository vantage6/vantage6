import re
import click

from pathlib import Path

from vantage6.common import info

pattern = r"(version_info\s*=\s*\(*)(\s*\d+,\s*\d+,\s*\d+,)(\s*)('\w*')(,\s*__build__\)*)"

def update_version_spec(spec: str) -> None:
    assert spec in ('final', 'beta', 'alpha', 'candidate')
    files = Path(".").rglob("_version.py")
    for file in files:
        info(f'File: {file}')
        info(f'Updating spec to: {spec}')
        with open(file, 'r') as f:
            content = f.read()
            new_content = re.sub(pattern, r"\1\2\3'{}'\5".format(spec), content)

        info(f'Writing to file')
        with open(file, 'w') as f:
            f.write(new_content)

def update_version(version: str) -> None:
    assert re.match(r"\d+.\d+.\d+", version)
    files = Path(".").rglob("_version.py")

    for file in files:
        info(f'File: {file}')
        info(f"Updating version to {version}")
        major, minor, patch = version.split(".")
        with open(file, 'r') as f:
            content = f.read()
            new_content = re.sub(pattern, r"\1 {}, {}, {},\3\4\5".format(major, minor, patch), content)

        info(f'Writing to file')
        with open(file, 'w') as f:
            f.write(new_content)

def update_build(build: int):
    files = Path(".").rglob("__build__")
    # info([file for file in files])
    for file in files:
        info(f'File: {file}')
        info(f"Updating build number to {build}")
        with open(file, 'w') as f:
            f.write(build)

@click.command()
@click.option('--spec', default=None, help="final, candidate, beta, alpha")
@click.option('--version', default=None, help="major.minor.patch")
@click.option('--build', default=None,
              help="build number for non-final versions")
def set_version(spec, version, build):

    if spec:
        update_version_spec(spec)
        info("Version specs updated")

    if version:
        update_version(version)
        info("Vesion numbers updated")

    if build:
        update_build(build)
        info("Build number updated")

if __name__ == '__main__':
    set_version()
