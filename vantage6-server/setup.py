import codecs
import os
from os import path
from pathlib import Path

from setuptools import find_namespace_packages, setup

# get current directory
here = Path(path.abspath(path.dirname(__file__)))
parent_dir = here.parent.absolute()

# get the long description from the README file
with codecs.open(path.join(parent_dir, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

# Read the API version from disk. This file should be located in the package
# folder, since it's also used to set the pkg.__version__ variable.
version_path = os.path.join(here, "vantage6", "server", "_version.py")
version_ns = {"__file__": version_path}
with codecs.open(version_path) as f:
    exec(f.read(), {}, version_ns)

# setup the package
setup(
    name="vantage6_server",
    version=version_ns["__version__"],
    description="Vantage6 server",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/vantage6/vantage6",
    packages=find_namespace_packages(),
    python_requires=">=3.13",
    install_requires=[
        "bcrypt==4.0.1",
        "flask==3.1.1",
        "flask-cors==6.0.0",
        "Flask-JWT-Extended==4.7.1",
        "Flask-Principal==0.4.0",
        "Flask-RESTful==0.3.10",
        "flask-marshmallow==0.15.0",
        "Flask-SocketIO==5.3.6",
        "gevent==25.4.2",
        "ipython==8.10.0",
        "kombu==5.2.4",
        "marshmallow==3.19.0",
        "names_generator==0.2.0",
        "prometheus-client==0.21.1",
        "pyjwt==2.9.0",
        "python-keycloak==5.5.0",
        "requests==2.32.4",
        "requests-oauthlib==1.3.1",
        "schema==0.7.5",
        "sqlalchemy==2.0.37",
        "werkzeug==3.1.3",
        f"vantage6 == {version_ns['__version__']}",
        f"vantage6-common == {version_ns['__version__']}",
    ],
    extras_require={
        "dev": [
            "coverage==6.4.4",
            "black",
            "pre-commit",
        ]
    },
    package_data={
        "vantage6.server": [
            "__build__",
            "_data/**/*.yaml",
            "server_data/*.yaml",
        ],
    },
    entry_points={
        "console_scripts": ["vserver-local=vantage6.server.cli.server:cli_server"]
    },
)
