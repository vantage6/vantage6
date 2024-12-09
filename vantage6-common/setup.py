import codecs
import os

from os import path
from setuptools import find_namespace_packages, setup
from pathlib import Path

# get current directory
here = Path(path.abspath(path.dirname(__file__)))
parent_dir = here.parent.absolute()

# get the long description from the README file
with codecs.open(path.join(parent_dir, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Read the API version from disk. This file should be located in the package
# folder, since it's also used to set the pkg.__version__ variable.
version_path = os.path.join(here, "vantage6", "common", "_version.py")
version_ns = {"__file__": version_path}
with codecs.open(version_path) as f:
    exec(f.read(), {}, version_ns)

# setup the package
setup(
    name="vantage6_common",
    version=version_ns["__version__"],
    description="Vantage6 common",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vantage6/vantage6",
    packages=find_namespace_packages(),
    python_requires=">=3.10",
    install_requires=[
        "appdirs==1.4.4",
        "click==8.1.3",
        "colorama==0.4.6",
        "cryptography==43.0.1",
        "docker>=7.1.0",
        "pyfiglet==0.8.post1",
        "PyJWT==2.6.0",
        "PyYAML>=6.0.1",
        "python-dateutil==2.8.2",
        "qrcode==7.3.1",
        "requests>=2.32.3",
        "schema==0.7.5",
        "setuptools>=67.8.0",
    ],
    extras_require={
        "dev": [
            "black",
            "pre-commit",
        ]
    },
    package_data={
        "vantage6.common": [
            "__build__",
        ],
    },
)
