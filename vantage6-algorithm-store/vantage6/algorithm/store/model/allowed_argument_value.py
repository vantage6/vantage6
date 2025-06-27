from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base


class AllowedArgumentValue(Base):
    """
    Table that describes which values are allowed for a specific argument.
    Allowed values are applicable if the argument is of type `int`, `string` or `float`.

    Each of these values is linked to an argument that is available in the
    class:`~.model.argument.Argument`

    Attributes
    ----------
    value : str
        An allowed value
    argument_id : str
        ID of the argument that this allowed value belongs to
    argument : :class:`~.model.argument.Argument`
        Argument that this allowed value belongs to
    """

    # fields
    value = Column(String)
    argument_id = Column(Integer, ForeignKey("argument.id"))

    # relationships
    argument = relationship("Argument", back_populates="allowed_values")
