from typing import Self

from sqlalchemy import Column, ForeignKey, Integer, String, select

from vantage6.server.model.base import Base, DatabaseSessionManager


class DataframeToBeDeletedAtNode(Base):
    """
    Table to store dataframes that are to be deleted at a node.

    The nodes are sent a socket event directly after creating a record in this table, or
    when they come online again. The node will then delete the dataframe from its local
    storage and remove the record from the table.
    """

    # fields
    dataframe_name = Column(String)
    session_id = Column(Integer, ForeignKey("session.id"))
    node_id = Column(Integer, ForeignKey("node.id"))

    @classmethod
    def get_by_node_id(cls, node_id: int) -> list["DataframeToBeDeletedAtNode"]:
        """
        Get all dataframe to be deleted at a node.
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalars(select(cls).filter_by(node_id=node_id)).all()
        session.commit()
        return result

    @classmethod
    def get_by_multiple_keys(
        cls, dataframe_name: str, session_id: int, node_id: int
    ) -> Self:
        """
        Get a dataframe to be deleted at a node by multiple keys.

        Parameters
        ----------
        dataframe_name: str
            Name of the dataframe to delete
        session_id: int
            ID of the session that contains the dataframe
        node_id: int
            ID of the node that is to delete the dataframe

        Returns
        -------
        DataframeToBeDeletedAtNode
            The dataframe to be deleted at a node
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalars(
            select(cls).filter_by(
                dataframe_name=dataframe_name, session_id=session_id, node_id=node_id
            )
        ).one()
        session.commit()
        return result
