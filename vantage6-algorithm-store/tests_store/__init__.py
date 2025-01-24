# TODO this has been added to __init__ to raise errors for sqlalchemy deprecations
# Should be removed when all deprecations are fixed
import warnings
from sqlalchemy import exc

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Enable SQLAlchemy deprecation warnings
warnings.filterwarnings("error", category=exc.RemovedIn20Warning)
