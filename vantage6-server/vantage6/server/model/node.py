import bcrypt

from vantage6.server.model.base import DatabaseSessionManager
from sqlalchemy.orm import relationship, validates
from sqlalchemy import Column, Integer, String, ForeignKey

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

    @validates("api_key")
    def _validate_api_key(self, key, api_key):
        return self.hash(api_key)

    def check_key(self, key):
        if self.api_key is not None:
            expected_hash = self.api_key.encode('utf8')
            return bcrypt.checkpw(key.encode('utf8'), expected_hash)
        return False

    @classmethod
    def get_by_api_key(cls, api_key):
        """returns Node based on the provided API key.

        Returns None if no Node is associated with api_key.
        """
        session = DatabaseSessionManager.get_session()

        nodes = session.query(cls).all()
        for node in nodes:
            is_correct_key = node.check_key(api_key)
            if is_correct_key:
                return node
        # no node found with matching API key
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
            f"{self.id}: '{self.name}', "
            f"organization: {self.organization.name}, "
            f"collaboration: {self.collaboration.name}, "
            f"api_key: {self.api_key} "
            ">"
        )
