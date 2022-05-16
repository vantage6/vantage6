from sqlalchemy import Column, Integer, ForeignKey, Table

from .base import Base


Member = Table(
    'Member',
    Base.metadata,
    Column('organization_id', Integer, ForeignKey('organization.id')),
    Column('collaboration_id', Integer, ForeignKey('collaboration.id'))
)
