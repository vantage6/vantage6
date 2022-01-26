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
version_path = os.path.join(here, 'vantage6', 'node', '_version.py')
version_ns = {
    '__file__': version_path
}
with open(version_path) as f:
    exec(f.read(), {}, version_ns)

# setup the package
setup(
    name='vantage6-node',
    version=version_ns['__version__'],
    description='vantage6 node',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/IKNL/vantage6-node',
    packages=find_namespace_packages(),
    python_requires='>=3.6',
    install_requires=[
        'requests==2.25.1',
        'gevent==20.9.0',
        'python-socketio[client]==5.5.0',
        'docker==4.2.0',
        'cryptography==3.3.2',
        'click==8.0.3',
        'termcolor==1.1.0',
        'bcrypt==3.1.7',
        f'vantage6 == {version_ns["__version__"]}',
        f'vantage6-client == {version_ns["__version__"]}',
    ],
    extras_require={
        'dev': [
            'coverage==4.5.4',
            'python-coveralls==2.9.3',
            'SQLAlchemy==1.3.15',
            'schema==0.7.1',
            'appdirs==1.4.3',
            'PyJWT==1.7.1',
            'Flask==1.1.1'
        ]
    },
    package_data={
        'vantage6.node': [
            '__build__',
            '_data/*.*',
        ],
    },
    entry_points={
        'console_scripts': [
            'vnode-local=vantage6.node.cli.node:cli_node'
        ]
    }
)
