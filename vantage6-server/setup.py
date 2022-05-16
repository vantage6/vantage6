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
version_path = os.path.join(here, 'vantage6', 'server', '_version.py')
version_ns = {
    '__file__': version_path
}
with open(version_path) as f:
    exec(f.read(), {}, version_ns)

# setup the package
setup(
    name='vantage6-server',
    version=version_ns['__version__'],
    description='Vantage6 server',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/IKNL/vantage6-server',
    packages=find_namespace_packages(),
    python_requires='>=3.6',
    install_requires=[
        'appdirs==1.4.3',
        'flask==1.1.1',
        'Flask-RESTful==0.3.8',
        'Flask-Cors==3.0.8',
        'Flask-JWT-Extended==3.24.1',
        'flask-marshmallow==0.11.0',
        'Flask-SocketIO==4.2.1',
        'SQLAlchemy==1.3.15',
        'Flask-Principal==0.4.0',
        'flasgger==0.9.5',
        'schema==0.7.1',
        'bcrypt==3.1.7',
        'questionary==1.5.2',
        'marshmallow==2.16.3',
        'marshmallow-sqlalchemy==0.15.0',
        'ipython==7.13.0',
        'requests==2.23.0',
        'psutil==5.7.0',
        'gevent==20.9.0',
        'gevent-websocket==0.10.1',
        'Flask-Mail==0.9.1',
        f'vantage6=={version_ns["__version__"]}',
        f'vantage6-common=={version_ns["__version__"]}',
        'gunicorn==19.9.0',
        'greenlet==0.4.17',
        'python-engineio==3.10.0',
        'python-socketio==4.4.0',
        'kombu==5.2.2'
    ],
    extras_require={
        'dev': [
            'termcolor==1.1.0',
            'coverage==4.5.4'
        ]
    },
    package_data={
        'vantage6.server': [
            '__build__',
            '_data/**/*.yaml',
            'server_data/*.yaml',
            'resource/swagger/*.yaml'
        ],
    },
    entry_points={
        'console_scripts': [
            'vserver-local=vantage6.server.cli.server:cli_server'
        ]
    }
)
