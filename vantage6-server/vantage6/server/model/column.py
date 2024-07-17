from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from vantage6.common.enums import TaskStatus
from vantage6.server.model.base import Base, DatabaseSessionManager

if TYPE_CHECKING:
    from vantage6.server.model import Session


class Column(Base):
    """
    Table to store column metadata in for a dataframe.

    Attributes
    ----------
    name : str
        column name
    type_ : int
        data type of the column
    dataframe_id : int
        ID of the last task that alters this session.

    Relationships
    -------------
    dataframe : :class:`~.model.Dataframe.Dataframe`
        Dataframe this column belongs to
    """

    # fields
    name = Column(String)
    type_ = Column("type", String)
    node_id = Column(Integer, ForeignKey("node.id"))
    dataframe_id = Column(Integer, ForeignKey("dataframe.id"))

    # relationships
    dataframe = relationship("Dataframe", back_populates="columns")
    node = relationship("Node", back_populates="columns")

    def __repr__(self):
        return (
            f"<Column {self.name}, "
            f"type: {self.type_}, "
            f"dataframe: {self.dataframe.handle}>"
        )
