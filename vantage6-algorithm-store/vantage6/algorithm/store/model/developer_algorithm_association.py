"""
The role_rule_assocation table defines which rules have been assigned to which
roles. Each line contains a rule_id that is a member of a certain role_id. Each
role will usually have multiple rules assigned to it.
"""
from sqlalchemy import Column, Integer, ForeignKey, Table

from .base import Base


developer_algorithm_association = Table(
    'developer_algorithm_association',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('user.id')),
    Column('algorithm_id', Integer, ForeignKey('algorithm.id'))
)
