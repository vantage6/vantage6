from sqlalchemy import Column, String, Boolean, exists
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from vantage6.server.model.base import Base, DatabaseSessionManager


class Collaboration(Base):
    """Combination of 2 or more Organizations."""

    # fields
    name = Column(String, unique=True)
    encrypted = Column(Boolean, default=1)

    # relationships
    organizations = relationship("Organization", secondary="Member",
                                 back_populates='collaborations')
    nodes = relationship("Node", back_populates="collaboration")
    tasks = relationship("Task", back_populates="collaboration")

    def get_organization_ids(self):
        return [organization.id for organization in self.organizations]

    def get_task_ids(self):
        return [task.id for task in self.tasks]

    def get_nodes_from_organizations(self, ids):
        """Returns a subset of nodes"""
        return [n for n in self.nodes if n.organization.id in ids]

    def get_node_from_organization(self, organization):
        for node in self.nodes:
            if node.organization.id == organization.id:
                return node
        return None

    @classmethod
    def find_by_name(cls, name):
        """Find collaboration by its name.

        If multiple collaborations share the same name, the first
        collaboration found is returned."""
        session = DatabaseSessionManager.get_session()
        try:
            return session.query(cls).filter_by(name=name).first()
        except NoResultFound:
            return None

    @classmethod
    def name_exists(cls, name):
        session = DatabaseSessionManager.get_session()
        return session.query(exists().where(cls.name == name)).scalar()

    def __repr__(self):
        number_of_organizations = len(self.organizations)
        number_of_tasks = len(self.tasks)
        return (
            "<Collaboration "
            f"{self.id}: '{self.name}', "
            f"{number_of_organizations} organization(s), "
            f"{number_of_tasks} task(s)"
            ">"
        )
