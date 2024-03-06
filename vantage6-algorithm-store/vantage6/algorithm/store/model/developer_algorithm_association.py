"""
The developer_algorithm_association table defines which user has created which algorithm.
"""

from sqlalchemy import Column, Integer, ForeignKey, Table

from .base import Base


developer_algorithm_association = Table(
    "developer_algorithm_association",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id")),
    Column("algorithm_id", Integer, ForeignKey("algorithm.id")),
)
