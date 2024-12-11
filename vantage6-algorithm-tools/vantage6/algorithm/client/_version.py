import os
import json

here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, "__build__")) as fp:
    __build__ = json.load(fp)

# Module version
version_info = (5, 0, 0, "alpha", __build__, 0)

# Module version stage suffix map
_specifier_ = {"alpha": "a", "beta": "b", "candidate": "rc", "final": ""}
version = f"{version_info[0]}.{version_info[1]}.{version_info[2]}"
pre_release = (
    ""
    if version_info[3] == "final"
    else "." + _specifier_[version_info[3]] + str(version_info[4])
)
post_release = "" if not version_info[5] else f".post{version_info[5]}"

# Module version accessible using thomas.__version__
__version__ = f"{version}{pre_release}{post_release}"
