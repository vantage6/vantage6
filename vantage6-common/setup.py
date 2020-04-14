from os import path
from codecs import open
from setuptools import setup, find_namespace_packages

# get current directory
here = path.abspath(path.dirname(__file__))

# get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# read the API version from disk
with open(path.join(here, 'vantage6', 'common', 'VERSION')) as fp:
    __version__ = fp.read()

# setup the package
setup(
    name='vantage6-common',
    version=__version__,
    description='Vantage6 common',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/IKNL/vantage6-common',
    packages=find_namespace_packages(),
    python_requires='>=3.6',
    install_requires=[
        'appdirs==1.4.3',
        'schema==0.7.1',
        'termcolor==1.1.0',
        'colorama==0.4.3',
        'click==7.1.1',
        'PyYAML==5.3.1'
    ],
    package_data={
        'vantage6.common': [
            'VERSION'
        ],
    }
)
