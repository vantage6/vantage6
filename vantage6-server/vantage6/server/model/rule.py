
from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from vantage6.server.model import Base


class Rule(Base):
    """Rules to determine permissions in an API endpoint.
    """

    # fields
    name = Column(Text)
    operation = Column(Integer)
    scope = Column(Integer)
    description = Column(String)

    # relationships
    roles = relationship("Role", back_populates="rules",
                         secondary="role_rule_association")

    def __repr__(self):
        return (
            f"<Rule {self.id}, "
            f"name: {self.name}, "
            f"operation: {self.operation}, "
            f"scope: {len(self.scope)}"
            ">"
        )
