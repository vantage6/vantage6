from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from vantage6.common.enums import RunStatus
from vantage6.server.model.base import Base, DatabaseSessionManager

if TYPE_CHECKING:
    from vantage6.server.model import Session


class Column(Base):
    """
    Table to store column metadata in for a dataframe. Each dataframe has a list of
    columns that are used to store the data. Each column has a name and a data type.
    Each node has its own dataframe, which is a collection of columns.

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
    name = Column(String)
    dtype = Column(String)
    node_id = Column(Integer, ForeignKey("node.id"))
    dataframe_id = Column(Integer, ForeignKey("dataframe.id"))

    # relationships
    dataframe = relationship("Dataframe", back_populates="columns")
    node = relationship("Node", back_populates="columns")

    def __repr__(self):
        return (
            f"<Column {self.name}, "
            f"dtype: {self.dtype}, "
            f"dataframe: {self.dataframe.handle}, "
            f"node: {self.node.name}>"
        )
