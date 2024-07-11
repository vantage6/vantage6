from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from vantage6.server.model.base import Base, DatabaseSessionManager

if TYPE_CHECKING:
    from vantage6.server.model.session import Session


class SessionConfig(Base):
    """
    Table to store session configuration by key-value pairs.

    This information includes e.g. which database handles are available to use.

    Attributes
    ----------
    session_id : int
        ID of the Session that this configuration belongs to
    key : str
        Key of the configuration
    value : str
        Value of the configuration

    Relationships
    -------------
    session : :class:`~.model.Session.Session`
        Session that this configuration belongs to
    """

    # fields
    session_id = Column("session_id", Integer, ForeignKey("session.id"))
    key = Column(String)
    value = Column(String)

    # relationships
    session = relationship("Session", back_populates="config")

    @classmethod
    def get_values_from_key(cls, session: "Session", key: str):
        """
        Get values for a given key within a specific session ID.

        Parameters
        ----------
        session : Session
            The Session model object to search for.
        key : str
            The key to search for.

        Returns
        -------
        list
            A list of values associated with the given key for the specified session ID.
        """
        sql_session = DatabaseSessionManager.get_session()

        try:
            result = (
                sql_session.query(cls).filter_by(session_id=session.id, key=key).all()
            )
            sql_session.commit()
            return result
        except NoResultFound:
            return None
