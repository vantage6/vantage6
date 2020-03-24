from os import path
from codecs import open
from setuptools import setup, find_namespace_packages

# get current directory
here = path.abspath(path.dirname(__file__))

# get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# read the API version from disk
with open(path.join(here, 'vantage6', 'client', 'VERSION')) as fp:
    __version__ = fp.read()

# setup the package
setup(
    name='vantage6-client',
    version=__version__,
    description='Vantage6 client',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/IKNL/vantage6-client',
    packages=find_namespace_packages(),
    python_requires='>=3.6',
    install_requires=[
       'cryptography==2.8',
       'requests==2.23.0'
    ],
    package_data={
        'vantage6.client': [
            'VERSION'
        ],
    }
)