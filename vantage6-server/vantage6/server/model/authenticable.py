from sqlalchemy import Column, String, DateTime

from .base import Base


class Authenticatable(Base):
    """Parent table of all entities that can authenticate.

    Entities that can authenticate are nodes and users. Containers
    can also authenticate but these are authenticated inderect
    through the nodes.
    """

    # fields
    type = Column(String(50))
    __mapper_args__ = {
        'polymorphic_identity': 'authenticatable',
        'polymorphic_on': type,
    }
    ip = Column(String)
    last_seen = Column(DateTime)
    status = Column(String)
