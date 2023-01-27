from sqlalchemy import Column, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from vantage6.server.model.base import Base, DatabaseSessionManager


class Role(Base):
    """Collection of Rules

    Attributes
    ----------
    name : str
        Name of the role
    description : str
        Description of the role
    organization_id : int
        Id of the organization this role belongs to
    rules : List[Rule]
        List of rules that belong to this role
    organization : Organization
        Organization this role belongs to
    users : List[User]
        List of users that belong to this role
    """

    # fields
    name = Column(Text)
    description = Column(Text)
    organization_id = Column(Integer, ForeignKey("organization.id"))

    # relationships
    rules = relationship("Rule", back_populates="roles",
                         secondary="role_rule_association")
    organization = relationship("Organization", back_populates="roles")
    users = relationship("User", back_populates="roles",
                         secondary="Permission")

    @classmethod
    def get_by_name(cls, name):
        session = DatabaseSessionManager.get_session()
        try:
            return session.query(cls).filter_by(name=name).first()
        except NoResultFound:
            return None

    def __repr__(self):
        return (
            f"<Role "
            f"{self.id}: '{self.name}', "
            f"description: {self.description}, "
            f"{len(self.users)} user(s)"
            ">"
        )
