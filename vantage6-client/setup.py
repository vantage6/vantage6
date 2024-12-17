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
version_path = os.path.join(here, "vantage6", "client", "_version.py")
version_ns = {"__file__": version_path}
with codecs.open(version_path) as f:
    exec(f.read(), {}, version_ns)


# setup the package
setup(
    name="vantage6_client",
    version=version_ns["__version__"],
    description="Vantage6 client",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vantage6/vantage6",
    packages=find_namespace_packages(),
    python_requires=">=3.10",
    install_requires=[
        "PyJWT==2.6.0",
        "pyfiglet==0.8.post1",
        "rich==13.5.2",
        f'vantage6-common=={version_ns["__version__"]}',
    ],
    extras_require={
        "dev": [
            "black",
            "pre-commit",
        ]
    },
    tests_require=["pytest"],
    package_data={
        "vantage6.client": [
            "__build__",
        ]
    },
)
