from os import path
from codecs import open
from setuptools import setup, find_namespace_packages

# get current directory
here = path.abspath(path.dirname(__file__))

# get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# read the API version from disk 
with open(path.join(here, 'vantage6', 'VERSION')) as fp:
    __version__ = fp.read()

# setup the package
setup(
    name='vantage6-node',
    version=__version__,
    description='vantage6 node',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/IKNL/vantage6-node',
    packages=find_namespace_packages(),
    python_requires='>=3.6',
    install_requires=[
        'requests==2.23.0',
        'gevent==1.4.0',
        'socketIO-client==0.7.2',
        'docker==4.2.0',
        'cryptography==2.8',
        'click==7.1.1',
        'termcolor==1.1.0',
        'bcrypt==3.1.7'
        # 'vantage6',
        # 'vantage6-client'
    ],
    extras_require={
        'dev':[
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
        'vantage6': [
            'VERSION',
            '_data/*.*'
        ],
    },
    entry_points={
        'console_scripts': [
            'vantage6-node=vantage6.node.cli.node:cli_node'
        ]
    }
)