from __future__ import annotations
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base


class Database(Base):
    """
    Table that describes database functions.

    Each of these databases is linked to a function within an algorithm. This
    describes which database is used by which function.

    Attributes
    ----------
    name : str
        Name of the database in the function
    description : str
        Description of the database
    function_id : int
        ID of the algorithm that this function belongs to
    function : :class:`~.model.algorithm.algorithm`
        Algorithm function that this database belongs to
    """

    # fields
    name = Column(String)
    description = Column(String)
    function_id = Column(Integer, ForeignKey("function.id"))

    # relationships
    function = relationship("Function", back_populates="databases")
