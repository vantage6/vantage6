from __future__ import annotations
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base


class Argument(Base):
    """
    Table that describes function arguments.

    Each of these arguments is linked to a function within an algorithm. This
    describes details on the arguments that are provided to the function.

    Attributes
    ----------
    name : str
        Name of the argument
    description : str
        Description of the argument
    function_id : int
        ID of the algorithm that this function belongs to
    type_ : str
        Type of the argument
    function : :class:`~.model.algorithm.algorithm`
        Algorithm function that this argument belongs to
    """

    # fields
    name = Column(String)
    description = Column(String)
    function_id = Column(Integer, ForeignKey("function.id"))
    type_ = Column("type", String)

    # relationships
    function = relationship("Function", back_populates="arguments")
