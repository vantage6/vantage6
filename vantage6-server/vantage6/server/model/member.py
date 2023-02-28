"""
The Member table is used to link organizations and collaborations together.
Each line in the table represents that a certain organization is member
of a certain collaboration by storing the ids of the organization and
collaboration.
"""
from sqlalchemy import Column, Integer, ForeignKey, Table

from .base import Base


Member = Table(
    'Member',
    Base.metadata,
    Column('organization_id', Integer, ForeignKey('organization.id')),
    Column('collaboration_id', Integer, ForeignKey('collaboration.id'))
)
