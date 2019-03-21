import os

__version__ = ''
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'VERSION')) as fp:
    __version__ = fp.read()
