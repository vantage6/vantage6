import os
from os import path
from codecs import open
from setuptools import setup, find_namespace_packages

# get current directory
here = path.abspath(path.dirname(__file__))

# get the long description from the README file
# with open(path.join(here, 'README.md'), encoding='utf-8') as f:
#     long_description = f.read()
long_description = (
    "GitHub: [https://github.com/iknl/vantage6]"
    "(https://github.com/iknl/vantage6)"
)

# Read the API version from disk. This file should be located in the package
# folder, since it's also used to set the pkg.__version__ variable.
version_path = os.path.join(here, 'vantage6', 'cli', '_version.py')
version_ns = {
    '__file__': version_path
}
with open(version_path) as f:
    exec(f.read(), {}, version_ns)


# setup the package
setup(
    name='vantage6',
    version=version_ns['__version__'],
    description='vantage6 command line interface',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/IKNL/vantage6',
    packages=find_namespace_packages(),
    python_requires='>=3.6',
    install_requires=[
        'schema==0.7.1',
        'click==7.1.1',
        'SQLAlchemy==1.3.15',
        'docker==4.2.0',
        'colorama==0.4.3',
        'questionary==1.5.2',
        'iPython==7.13.0',
        'SQLAlchemy==1.3.15',
        f'vantage6-common=={version_ns["__version__"]}',
        f'vantage6-client=={version_ns["__version__"]}',
    ],
    extras_require={
        'dev': [
            'coverage==4.5.4'
        ]
    },
    package_data={
        'vantage6.cli': [
            '__build__',
        ],
    },
    entry_points={
        'console_scripts': [
            'vnode=vantage6.cli.node:cli_node',
            'vserver=vantage6.cli.server:cli_server'
        ]
    }
)
