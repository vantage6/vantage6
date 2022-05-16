from sqlalchemy import Column, Integer, ForeignKey, Table

from .base import Base


role_rule_association = Table(
    'role_rule_association',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('role.id')),
    Column('rule_id', Integer, ForeignKey('rule.id'))
)
