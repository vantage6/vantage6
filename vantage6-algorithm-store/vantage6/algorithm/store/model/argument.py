from __future__ import annotations
from sqlalchemy import Column, String, ForeignKey, Integer, Boolean, select
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager


class Argument(Base):
    """
    Table that describes function arguments.

    Each of these arguments is linked to a function within an algorithm. This
    describes details on the arguments that are provided to the function.

    Attributes
    ----------
    name : str
        Name of the argument
    display_name : str
        Display name of the argument
    description : str
        Description of the argument
    function_id : int
        ID of the algorithm that this function belongs to
    type_ : str
        Type of the argument
    has_default_value : bool
        Whether the argument has a default value
    default_value : str
        Default value of the argument
    conditional_on_id : int
        ID of the argument that this argument is conditional on
    conditional_operator : str
        Comparator used for the conditional argument
    conditional_value : str
        Value that the argument should be compared to
    is_frontend_only : bool
        Whether the argument should be passed to the algorithm or should only be shown
        in the UI form
    function : :class:`~.model.algorithm.algorithm`
        Algorithm function that this argument belongs to
    """

    # fields
    name = Column(String)
    display_name = Column(String)
    description = Column(String)
    function_id = Column(Integer, ForeignKey("function.id"))
    type_ = Column("type", String)
    # note that we have both column 'has_default_value' and 'default_value' because the
    # default value itself can be NULL
    has_default_value = Column(Boolean, default=False)
    default_value = Column(String)
    # columns for conditional arguments
    conditional_on_id = Column(Integer, ForeignKey("argument.id"))
    conditional_operator = Column(String)
    conditional_value = Column(String)
    # flag arguments that should not be passed to the algorithm
    is_frontend_only = Column(Boolean, default=False)

    # relationships
    function = relationship("Function", back_populates="arguments")
    conditional_argument = relationship(
        "Argument",
        backref="dependent_arguments",
        remote_side="Argument.id",
    )

    @classmethod
    def get_by_name(cls, name: str, function_id: int) -> Argument | None:
        """
        Get an argument by its name

        Parameters
        ----------
        name : str
            Name of the argument to get
        function_id : int
            ID of the function that the argument belongs to

        Returns
        -------
        Argument
            The argument with the given name
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalars(
            select(cls).filter_by(name=name, function_id=function_id)
        ).first()
        session.commit()
        return result
