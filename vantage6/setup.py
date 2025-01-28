import codecs
import os

from os import path
from codecs import open
from setuptools import setup, find_namespace_packages
from pathlib import Path

# get current directory
here = Path(path.abspath(path.dirname(__file__)))
parent_dir = here.parent.absolute()

# get the long description from the README file
with codecs.open(path.join(parent_dir, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Read the API version from disk. This file should be located in the package
# folder, since it's also used to set the pkg.__version__ variable.
version_path = os.path.join(here, "vantage6", "cli", "_version.py")
version_ns = {"__file__": version_path}
with open(version_path) as f:
    exec(f.read(), {}, version_ns)


# setup the package
setup(
    name="vantage6",
    version=version_ns["__version__"],
    description="vantage6 command line interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vantage6/vantage6",
    packages=find_namespace_packages(),
    python_requires=">=3.10",
    install_requires=[
        "click==8.1.3",
        "colorama==0.4.6",
        "copier==9.2.0",
        "docker==7.1.0",
        "ipython==8.10.0",
        "jinja2==3.1.5",
        "pandas>=1.5.3",
        "questionary==1.10.0",
        "rich==13.5.2",
        "schema==0.7.5",
        "sqlalchemy==2.0.37",
        f'vantage6-common == {version_ns["__version__"]}',
        f'vantage6-client == {version_ns["__version__"]}',
    ],
    extras_require={
        "dev": [
            "coverage==6.4.4",
            "black",
            "pre-commit",
        ]
    },
    package_data={
        "vantage6.cli": [
            "__build__",
            "rabbitmq/rabbitmq.config",
            "template/node_config.j2",
            "template/server_config.j2",
            "template/server_import_config.j2",
            "template/algo_store_config.j2",
            "dev/data/olympic_athletes_2016.csv",
        ],
    },
    entry_points={
        "console_scripts": [
            "v6=vantage6.cli.cli:cli_complete",
            # TODO v5+ remove vnode/vserver/vdev aliases (?)
            "vnode=vantage6.cli.cli:cli_node",
            "vserver=vantage6.cli.cli:cli_server",
            "vdev=vantage6.cli.cli:cli_dev",
        ]
    },
)
