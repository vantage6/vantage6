from __future__ import annotations
from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base


class Function(Base):
    """
    Table that describes which functions are available.

    Each of these functions is linked to an algorithm that is available in the
    class:`~.model.algorithm.algorithm`.

    Attributes
    ----------
    name : str
        Name of the function
    description : str
        Description of the function
    type_ : str
        Type of function
    algorithm_id : int
        ID of the algorithm that this function belongs to
    algorithm : :class:`~.model.algorithm.algorithm`
        Algorithm that this function belongs to
    databases : list[:class:`~.model.database.database`]
        List of databases that this function uses
    arguments : list[:class:`~.model.argument.argument`]
        List of arguments that this function uses
    """

    # fields
    name = Column(String)
    description = Column(String)
    type_ = Column("type", String)
    algorithm_id = Column(Integer, ForeignKey("algorithm.id"))

    # relationships
    algorithm = relationship("Algorithm", back_populates="functions")
    databases = relationship("Database", back_populates="function")
    arguments = relationship("Argument", back_populates="function")
    # output = relationship("Output", back_populates='function')
