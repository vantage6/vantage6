import codecs
import os

from os import path
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
version_path = os.path.join(here, "vantage6", "node", "_version.py")
version_ns = {"__file__": version_path}
with codecs.open(version_path) as f:
    exec(f.read(), {}, version_ns)

# setup the package
setup(
    name="vantage6-node",
    version=version_ns["__version__"],
    description="vantage6 node",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vantage6/vantage6",
    packages=find_namespace_packages(),
    python_requires=">=3.10",
    install_requires=[
        "click==8.1.3",
        "docker==6.1.2",
        "gevent==23.9.1",
        "jinja2==3.1.4",
        "python-socketio==5.7.2",
        "requests==2.31.0",
        f'vantage6 == {version_ns["__version__"]}',
        f'vantage6-client == {version_ns["__version__"]}',
        f'vantage6-algorithm-tools == {version_ns["__version__"]}',
    ],
    extras_require={
        "dev": [
            "coverage==6.4.4",
            "python-coveralls==2.9.3",
            "SQLAlchemy==1.4.46",
            "schema==0.7.5",
            "appdirs==1.4.4",
            "flask==2.2.5",
            "black",
            "pre-commit",
        ]
    },
    package_data={
        "vantage6.node": [
            "__build__",
            "_data/*.*",
        ],
    },
    entry_points={"console_scripts": ["vnode-local=vantage6.node.cli.node:cli_node"]},
)
