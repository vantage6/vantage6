from __future__ import annotations
import enum
from sqlalchemy import Column, String, ForeignKey, Enum
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base


class ArgumentType(str, enum.Enum):
    """ Enum for argument types """
    COLUMN = "column"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    JSON = "json"
    ORGANIZATIONS = "organizations"
    ORGANIZATION = "organization"


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
    function_id : str
        ID of the algorithm that this function belongs to
    function : :class:`~.model.algorithm.algorithm`
        Algorithm function that this argument belongs to
    """

    # fields
    name = Column(String)
    description = Column(String)
    function_id = Column(String, ForeignKey('function.id'))
    type = Column(Enum(ArgumentType))

    # relationships
    function = relationship("Function", back_populates='arguments')
