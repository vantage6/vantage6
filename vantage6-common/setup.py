import codecs
import os

from os import path
from setuptools import find_namespace_packages, setup

# get current directory
here = path.abspath(path.dirname(__file__))

# get the long description from the README file
with codecs.open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read the API version from disk. This file should be located in the package
# folder, since it's also used to set the pkg.__version__ variable.
version_path = os.path.join(here, 'vantage6', 'common', '_version.py')
version_ns = {
    '__file__': version_path
}
with codecs.open(version_path) as f:
    exec(f.read(), {}, version_ns)

# setup the package
setup(
    name='vantage6-common',
    version=version_ns['__version__'],
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
        'click==8.0.3',
        'PyYAML==5.4',
        'python-dateutil==2.8.1',
        'docker==4.2.0',
        'pyfiglet==0.8.post1'
    ],
    package_data={
        'vantage6.common': [
            '__build__',
        ],
    }
)
