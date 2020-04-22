import os
import json

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, '__build__')) as fp:
    __build__ = json.load(fp)

# Module version
version_info = (0, 1, 0, 'alpha', __build__)

# Module version stage suffix map
_specifier_ = {'alpha': 'a', 'beta': 'b', 'candidate': 'rc', 'final': ''}

# Module version accessible using thomas.__version__
__version__ = '%s.%s.%s%s'%(version_info[0], version_info[1], version_info[2],
  '' if version_info[3]=='final' else _specifier_[version_info[3]]+str(version_info[4]))
