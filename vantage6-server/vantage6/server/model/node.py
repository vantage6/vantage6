from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.model.authenticable import Authenticatable


class Node(Authenticatable):
    """Application that executes Tasks."""
    _hidden_attributes = ['api_key']

    id = Column(Integer, ForeignKey('authenticatable.id'), primary_key=True)

    # fields
    name = Column(String)
    api_key = Column(String)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"))
    organization_id = Column(Integer, ForeignKey("organization.id"))

    # relationships
    collaboration = relationship("Collaboration", back_populates='nodes')
    organization = relationship("Organization", back_populates='nodes')

    # the type specification in Authenticatable
    __mapper_args__ = {
        'polymorphic_identity': 'node',
    }

    @classmethod
    def get_by_api_key(cls, api_key):
        """returns Node based on the provided API key.

        Returns None if no Node is associated with api_key.
        """
        session = DatabaseSessionManager.get_session()

        try:
            return session.query(cls).filter_by(api_key=api_key).one()
        except NoResultFound:
            return None

    @classmethod
    def exists(cls, organization_id, collaboration_id):
        session = DatabaseSessionManager.get_session()
        return session.query(cls).filter_by(
            organization_id=organization_id,
            collaboration_id=collaboration_id
        ).scalar()

    def __repr__(self):
        return (
            "<Node "
            f"{self.id}: {self.name}, "
            f"organization: {self.organization.name}, "
            f"collaboration: {self.collaboration.name}, "
            f"api_key: {self.api_key} "
            ">"
        )
