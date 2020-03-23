from sqlalchemy import Column, String, Boolean
from sqlalchemy.orm import Session, relationship
from sqlalchemy.orm.exc import NoResultFound

from .base import Base, Database

class Collaboration(Base):
    """Combination of 2 or more Organizations."""
    
    # fields
    name = Column(String)
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
        session = Database().Session
        try:
            return session.query(cls).filter_by(name=name).first()
        except NoResultFound:
            return None
        
    def __repr__(self):
        number_of_organizations = len(self.organizations)
        number_of_tasks = len(self.tasks)
        return ("<Collaboration "
            f"number of tasks: {number_of_tasks}, "
            f"number of organizations: {number_of_organizations}"
        ">")
