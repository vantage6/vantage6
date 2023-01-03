import re
import click

from pathlib import Path

# from vantage6.common import info
def info(msg):
    print(msg)

pattern = r"(version_info\s*=\s*\(*)(\s*\d+,\s*\d+,\s*\d+,)(\s*)('\w*')(,\s*__build__)(,\s*)(\d+)(\)*)"

def update_version_spec(spec: str) -> None:
    assert spec in ('final', 'beta', 'alpha', 'candidate')
    files = [file_ for file_ in Path("../").rglob("_version.py") if \
        'build' not in str(file_)]
    info(f'found files={files}')
    for file in files:
        info(f'File: {file}')
        info(f'Updating spec to: {spec}')
        with open(file, 'r') as f:
            content = f.read()
            new_content = re.sub(pattern, r"\1\2\g<3>'{}'\5\6\7\8".format(spec), content)

        info(f'Writing to file')
        with open(file, 'w') as f:
            f.write(new_content)

def update_version(version: str) -> None:
    print(version)
    assert re.match(r"\d+.\d+.\d+", version)
    files = [file_ for file_ in Path("../").rglob("_version.py") if \
        'build' not in str(file_)]

    for file in files:
        info(f'File: {file}')
        info(f"Updating version to {version}")
        major, minor, patch = version.split(".")
        with open(file, 'r') as f:
            content = f.read()
            new_content = re.sub(pattern, r"\1{}, {}, {},\3\4\5\6\7\8".format(major, minor, patch), content)

        info(f'Writing to file')
        with open(file, 'w') as f:
            f.write(new_content)

def update_build(build: int):
    files = Path("../").rglob("__build__")
    info(f"Updating build number to {build}")
    for file in files:
        info(f'File: {file}')
        with open(file, 'w') as f:
            f.write(build)

def update_post(post):
    files = [file_ for file_ in Path("../").rglob("_version.py") if \
        'build' not in str(file_)]
    info(f"Setting post-release version to: {post}")
    for file_ in files:
        info(f'File: {file_}')
        with open(file_, 'r') as f:
            content = f.read()
            new_content = re.sub(pattern, r"\1\2\3\4\5\g<6>{}\8".format(post), content)

        info(f'Writing to file')
        with open(file_, 'w') as f:
            f.write(new_content)


@click.command()
@click.option('--spec', default='final', help="final, candidate, beta, alpha")
@click.option('--version', default='0.0.0', help="major.minor.patch")
@click.option('--build', default="0",
              help="build number for non-final versions")
@click.option('--post', default="0", help=".postN")
def set_version(spec, version, build, post):

    update_version_spec(spec)
    info("Version specs updated")

    update_version(version)
    info("Vesion numbers updated")

    update_build(str(build))
    info("Build number updated")

    update_post(str(post))
    info("Post release version set")


if __name__ == '__main__':
    set_version()
