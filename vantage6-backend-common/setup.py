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
version_path = os.path.join(here, "vantage6", "backend", "common", "_version.py")
version_ns = {"__file__": version_path}
with codecs.open(version_path) as f:
    exec(f.read(), {}, version_ns)

# setup the package
setup(
    name="vantage6_backend_common",
    version=version_ns["__version__"],
    description="Vantage6 common backend functionalities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vantage6/vantage6",
    packages=find_namespace_packages(),
    python_requires=">=3.10",
    install_requires=[
        "flask==3.1.1",
        "flask-mail==0.9.1",
        "Flask-RESTful==0.3.10",
        "marshmallow==3.19.0",
        "marshmallow-sqlalchemy==0.29.0",
        "SQLAlchemy==1.4.46",
        "prometheus-client==0.21.1",
        f'vantage6-common == {version_ns["__version__"]}',
    ],
    extras_require={"dev": ["coverage==6.4.4"]},
    package_data={
        "vantage6.backend.common": [
            "__build__",
        ],
    },
)
