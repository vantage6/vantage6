import base64

from sqlalchemy import Column, String, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.exc import NoResultFound

from vantage6.common.globals import STRING_ENCODING
from vantage6.server.model.base import Base, DatabaseSessionManager


class Organization(Base):
    """A legal entity.

    An organization plays a central role in managing distributed tasks. Each
    Organization contains a public key which other organizations can use to
    send encrypted messages that only this organization can read.
    """

    # fields
    name = Column(String)
    domain = Column(String)
    address1 = Column(String)
    address2 = Column(String)
    zipcode = Column(String)
    country = Column(String)
    _public_key = Column(LargeBinary)

    # relations
    collaborations = relationship("Collaboration", secondary="Member",
                                  back_populates="organizations")
    results = relationship("Result", back_populates="organization")
    nodes = relationship("Node", back_populates="organization")
    users = relationship("User", back_populates="organization")
    created_tasks = relationship("Task", back_populates="initiator")
    roles = relationship("Role", back_populates="organization")

    def get_result_ids(self):
        # FIXME this should be removed in version 4.0 and above
        # note that the import below is required since this file (Organization)
        # is already imported in model.Result
        from vantage6.server.model.result import Result
        session = DatabaseSessionManager.get_session()
        return session.query(Result.id)\
                      .filter(Result.organization_id == self.id).all()

    @classmethod
    def get_by_name(cls, name):
        session = DatabaseSessionManager.get_session()
        try:
            return session.query(cls).filter_by(name=name).first()
        except NoResultFound:
            return None

    @hybrid_property
    def public_key(self):
        if self._public_key:
            # TODO this should be fixed properly
            try:
                return base64.b64decode(self._public_key)\
                    .decode(STRING_ENCODING)
            except Exception:
                return ""
        else:
            return ""

    @public_key.setter
    def public_key(self, public_key_b64):
        """Assumes that the public key is in b64-encoded."""
        self._public_key = base64.b64decode(
            public_key_b64.encode(STRING_ENCODING)
        )

    def __repr__(self):
        number_of_users = len(self.users)
        return (
            "<Organization "
            f"{self.id}: '{self.name}', "
            f"domain:{self.domain}, "
            f"users:{number_of_users}"
            ">"
        )
