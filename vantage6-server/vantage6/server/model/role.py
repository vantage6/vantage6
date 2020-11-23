
from sqlalchemy import Column, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from vantage6.server.model import Base


class Role(Base):
    """Collection of Rules
    """

    # fields
    name = Column(Text)
    description = Column(Text)
    organization_id = Column(Integer, ForeignKey("organization.id"),
                             nullable=False)

    # relationships
    rules = relationship("Rule", back_populates="roles",
                         secondary="role_rule_association")
    organization = relationship("Organization", back_populates="roles")
    users = relationship("User", back_populates="roles",
                         secondary="Permission")

    def __repr__(self):
        return (
            f"<Role {self.id}, "
            f"name: {self.name}, "
            f"description: {self.description}, "
            f"users: {len(self.users)}"
            ">"
        )
