"""
The role_rule_assocation table defines which rules have been assigned to which
roles. Each line contains a rule_id that is a member of a certain role_id. Each
role will usually have multiple rules assigned to it.
"""

from sqlalchemy import Column, Integer, ForeignKey, Table

from .base import Base

# TODO: refactor to use the server model
role_rule_association = Table(
    "role_rule_association",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("role.id")),
    Column("rule_id", Integer, ForeignKey("rule.id")),
)
