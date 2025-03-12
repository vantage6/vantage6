from sqlalchemy import Column as Column_, Integer, ForeignKey, String, and_, select
from sqlalchemy.orm import relationship

from vantage6.server.model.base import Base, DatabaseSessionManager


class Column(Base):
    """
    Table to store column metadata in for a dataframe.

    A session contains one or more data extractions stored as dataframes.
    Each dataframe is requested for each node. The nodes then return the
    columns that they have available for that dataframe. This table thus stores which
    columns are available for a certain node in a session's dataframe.

    Attributes
    ----------
    name : str
        column name
    dtype : int
        data type of the column
    node_id : int
        ID of the node that this column belongs to
    dataframe_id : int
        ID of the last task that alters this session.

    Relationships
    -------------
    dataframe : :class:`~.model.Dataframe.Dataframe`
        Dataframe this column belongs to
    node : :class:`~.model.Node.Node`
        Node this column belongs to
    """

    # fields
    name = Column_(String)
    dtype = Column_(String)
    node_id = Column_(Integer, ForeignKey("node.id"))
    dataframe_id = Column_(Integer, ForeignKey("dataframe.id"))

    # relationships
    dataframe = relationship("Dataframe", back_populates="columns")
    node = relationship("Node", back_populates="columns")

    @classmethod
    def clear(cls, dataframe_id: int, node_id: int) -> None:
        """
        Remove all columns from the dataframe.

        Parameters
        ----------
        dataframe_id : int
            ID of the dataframe to remove all columns from
        """
        session = DatabaseSessionManager.get_session()
        session.scalars(
            select(cls).filter(
                and_(cls.dataframe_id == dataframe_id, cls.node_id == node_id)
            )
        ).delete()
        session.commit()

    def __repr__(self):
        return (
            f"<Column {self.name}, "
            f"dtype: {self.dtype}, "
            f"dataframe: {self.dataframe.name}, "
            f"node: {self.node.name}>"
        )
