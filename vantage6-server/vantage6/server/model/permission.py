from sqlalchemy import Column, Integer, ForeignKey, Table

from .base import Base


Permission = Table(
    'Permission',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('role.id')),
    Column('user_id', Integer, ForeignKey('user.id'))
)