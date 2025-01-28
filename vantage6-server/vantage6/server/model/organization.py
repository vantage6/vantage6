from __future__ import annotations
import base64

from sqlalchemy import Column, String, LargeBinary, select
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.exc import NoResultFound

from vantage6.common.globals import STRING_ENCODING
from vantage6.server.model.base import Base, DatabaseSessionManager


class Organization(Base):
    """Table that describes which organizations are available.

    An organization is the legal entity that plays a central role in managing tasks.
    Each organization contains a public key which other organizations can use to send
    encrypted messages that only this organization can read.

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

    Relationships
    -------------
    collaborations :
            list[:class:`~vantage6.server.model.collaboration.Collaboration`]
        List of collaborations that this organization is part of
    runs : list[:class:`~vantage6.server.model.run.Run`]
        List of runs that are part of this organization
    nodes : list[:class:`~vantage6.server.model.node.Node`]
        List of nodes that are part of this organization
    users : list[:class:`~vantage6.server.model.user.User`]
        List of users that are part of this organization
    tasks : list[:class:`~vantage6.server.model.task.Task`]
        List of tasks that are created by this organization
    roles : list[:class:`~vantage6.server.model.role.Role`]
        List of roles that are available to this organization
    studies : list[:class:`~vantage6.server.model.study.Study`]
        List of studies that are part of this organization
    """

    # fields
    name = Column(String, unique=True)
    domain = Column(String)
    address1 = Column(String)
    address2 = Column(String)
    zipcode = Column(String)
    country = Column(String)
    _public_key = Column(LargeBinary)

    # relations
    collaborations = relationship(
        "Collaboration", secondary="Member", back_populates="organizations"
    )
    runs = relationship("Run", back_populates="organization")
    nodes = relationship("Node", back_populates="organization")
    users = relationship("User", back_populates="organization")
    tasks = relationship("Task", back_populates="init_org")
    roles = relationship("Role", back_populates="organization")
    studies = relationship(
        "Study", secondary="StudyMember", back_populates="organizations"
    )

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
            result = session.scalars(select(cls).filter_by(name=name)).first()
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
                return base64.b64decode(self._public_key).decode(STRING_ENCODING)
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
        self._public_key = base64.b64decode(public_key_b64.encode(STRING_ENCODING))

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
