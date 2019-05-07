from sqlalchemy import Column, String
from sqlalchemy.orm import Session, relationship

from .base import Base, Database

class Collaboration(Base):
    """Combination of 2 or more Organizations."""
    __tablename__ = "collaboration"
    
    # fields
    name = Column(String)

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

    # TODO rename to 'find_by_name'
    @classmethod
    def get_collaboration_by_name(cls, name):
        """Find collaboration by its name. 
        
        If multiple collaborations share the same name, the first 
        collaboration found is returned."""
        session = Database().Session
        try:
            return session.query(cls).filter_by(name=name).first()
        except NoResultFound:
            return None
        
    def __repr__(self):
        number_of_organizations = len(self.organizations)
        number_of_tasks = len(self.tasks)
        return ("<"
            f"number of tasks: {number_of_tasks}, "
            f"number of organizations: {number_of_organizations}"
        ">")
