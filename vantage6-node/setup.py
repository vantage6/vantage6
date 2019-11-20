"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


# Read the API version from disk 
with open(path.join(here, 'vantage', 'VERSION')) as fp:
    __version__ = fp.read()


# Setup the package
setup(
    name='vantage',
    version=__version__,
    description='Package and utilities for distributed learning',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/IKNL/vantage',
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    python_requires='>=3',
    install_requires=[
        'appdirs',
        'bcrypt',
        'click',
        'colorama',
        'docker',
        'eventlet',
        'flask',
        'flask-cors',
        'flask-jwt-extended',
        'flask-restful',
        'flask-sqlalchemy',
        'flask-marshmallow',
        'flask-socketio',
        'socketIO_client',
        'marshmallow==2.16.3',
        'marshmallow-sqlalchemy==0.15.0',
        'pyyaml',
        'psutil',
        'psycopg2-binary',
        'requests',
        'termcolor',
        'sqlalchemy',
        'iknl-flasgger',
        'schema',
        'questionary',
        'ipython',
        'cryptography',
        'gevent'
    ],
    package_data={  
        'vantage': [
            'server/server.wsgi', 
            'VERSION', 
            '_data/**/*.yaml',
            '_data/*.yaml',
            'server/resource/swagger/*.yaml'
        ],
    },
    entry_points={
        'console_scripts': [
            'vnode=vantage.node_manager.cli.node_manager:cli_node',
            'vserver=vantage.server.cli.server:cli_server',
            'vdev=vantage.util.cli.develop:cli_develop'
        ],
    }
)

