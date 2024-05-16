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
version_path = os.path.join(here, "vantage6", "algorithm", "store", "_version.py")
version_ns = {"__file__": version_path}
with codecs.open(version_path) as f:
    exec(f.read(), {}, version_ns)

# setup the package
setup(
    name="vantage6-algorithm-store",
    version=version_ns["__version__"],
    description="Vantage6 algorithm store",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vantage6/vantage6",
    packages=find_namespace_packages(),
    python_requires=">=3.10",
    install_requires=[
        "flasgger==0.9.5",
        "flask==2.2.5",
        "Flask-Cors==3.0.10",
        "Flask-Principal==0.4.0",
        "flask-marshmallow==0.15.0",
        "Flask-RESTful==0.3.10",
        "gevent==23.9.1",
        "jsonschema==4.21.1",
        "marshmallow==3.19.0",
        "requests==2.31.0",
        "schema==0.7.5",
        "SQLAlchemy==1.4.46",
        "werkzeug==3.0.3",
        f'vantage6 == {version_ns["__version__"]}',
        f'vantage6-common == {version_ns["__version__"]}',
    ],
    extras_require={"dev": ["coverage==6.4.4"]},
    package_data={
        "vantage6.algorithm.store": [
            "__build__",
        ],
    },
)
