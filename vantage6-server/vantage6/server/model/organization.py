from __future__ import annotations
import base64

from sqlalchemy import Column, String, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.exc import NoResultFound

from vantage6.common.globals import STRING_ENCODING
from vantage6.server.model.base import Base, DatabaseSessionManager


class Organization(Base):
    """Table that describes which organizations are available.

    An organization is the legal entity that plays a central role in managing
    distributed tasks. Each organization contains a public key which other
    organizations can use to send encrypted messages that only this
    organization can read.

    Attributes
    ----------
    name : str
        Name of the organization
    domain : str
        Domain of the organization
    address1 : str
        Address of the organization
    address2 : str
        Address of the organization
    zipcode : str
        Zipcode of the organization
    country : str
        Country of the organization
    _public_key : bytes
        Public key of the organization
    collaborations : list[Collaboration]
        List of collaborations that this organization is part of
    results : list[:class:`~vantage6.server.model.result.Result`]
        List of results that are part of this organization
    nodes : list[:class:`~vantage6.server.model.node.Node`]
        List of nodes that are part of this organization
    users : list[User]
        List of users that are part of this organization
    created_tasks : list[Task]
        List of tasks that are created by this organization
    roles : list[Role]

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

    def get_result_ids(self) -> list[int]:
        """
        Returns a list of result ids that are part of this organization.

        Returns
        -------
        list[int]
            List of result ids
        """
        # FIXME this should be removed in version 4.0 and above
        # note that the import below is required since this file (Organization)
        # is already imported in model.Result
        from vantage6.server.model.result import Result
        session = DatabaseSessionManager.get_session()
        result_ids = session.query(Result.id)\
                            .filter(Result.organization_id == self.id).all()
        session.commit()
        return result_ids

    @classmethod
    def get_by_name(cls, name) -> Organization | None:
        """
        Returns the organization with the given name.

        Parameters
        ----------
        name : str
            Name of the organization

        Returns
        -------
        Organization | None
            Organization with the given name if it exists, otherwise None
        """
        session = DatabaseSessionManager.get_session()
        try:
            result = session.query(cls).filter_by(name=name).first()
            session.commit()
            return result
        except NoResultFound:
            return None

    @hybrid_property
    def public_key(self) -> str:
        """
        Returns the public key of the organization.

        Returns
        -------
        str
            Public key of the organization. Empty string if no public key is
            set.
        """
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
    def public_key(self, public_key_b64: str) -> None:
        """
        Set public key of the organization. Assumes that the public key is
        already b64-encoded.

        Parameters
        ----------
        public_key_b64 : str
            Public key of the organization, b64-encoded
        """
        self._public_key = base64.b64decode(
            public_key_b64.encode(STRING_ENCODING)
        )

    def __repr__(self) -> str:
        """
        Returns a string representation of the organization.

        Returns
        -------
        str
            String representation of the organization
        """
        number_of_users = len(self.users)
        return (
            "<Organization "
            f"{self.id}: '{self.name}', "
            f"domain:{self.domain}, "
            f"users:{number_of_users}"
            ">"
        )
