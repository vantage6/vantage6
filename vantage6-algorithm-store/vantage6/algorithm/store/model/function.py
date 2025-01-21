from sqlalchemy import Boolean, Column, String, ForeignKey, Integer
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
    display_name : str
        Display name of the function
    description : str
        Description of the function
    type_ : str
        Type of function
    standalone : bool
        Whether this function produces useful results when running it by itself
    algorithm_id : int
        ID of the algorithm that this function belongs to
    algorithm : :class:`~.model.algorithm.Algorithm`
        Algorithm that this function belongs to
    databases : list[:class:`~.model.database.Database`]
        List of databases that this function uses
    arguments : list[:class:`~.model.argument.Argument`]
        List of arguments that this function uses
    ui_visualizations : list[:class:`~.model.ui_visualization.UIVisualization`]
        List of user interface visualizations that this function produces
    """

    # fields
    name = Column(String)
    display_name = Column(String)
    description = Column(String)
    type_ = Column("type", String)
    algorithm_id = Column(Integer, ForeignKey("algorithm.id"))
    standalone = Column(Boolean, default=True)

    # relationships
    algorithm = relationship("Algorithm", back_populates="functions")
    databases = relationship("Database", back_populates="function")
    arguments = relationship("Argument", back_populates="function")
    ui_visualizations = relationship("UIVisualization", back_populates="function")
