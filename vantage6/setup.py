from os import path
from codecs import open
from setuptools import setup, find_namespace_packages

# get current directory
here = path.abspath(path.dirname(__file__))

# get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# read the API version from disk
with open(path.join(here, 'vantage6', 'cli', 'VERSION')) as fp:
    __version__ = fp.read()

# setup the package
setup(
    name='vantage6',
    version=__version__,
    description='vantage6 command line interface',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/IKNL/vantage6',
    packages=find_namespace_packages(),
    python_requires='>=3.6',
    install_requires=[
        'docker==4.2.0',
        'colorama==0.4.3',
        'questionary==1.5.1',
        'iPython==7.13.0',
        'SQLAlchemy==1.3.15'
        'vantage6-common'
    ],
    extras_require={
        'dev': [
            'coverage==5.0.4'
        ]
    },
    package_data={
        'vantage6.cli': [
            'VERSION',
            '_data/*.*'
        ],
    },
    entry_points={
        'console_scripts': [
            'vnode=vantage6.cli.node:cli_node',
            'vserver=vantage6.cli.server:cli_server'
        ]
    }
)