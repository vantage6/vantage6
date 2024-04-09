from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base


class UIVisualization(Base):
    """
    Table that describes how the algorithm should be visualized in the UI.

    Attributes
    ----------
    name : str
        Name of the visualization
    description: str
        Description of the visualization
    type_: str
        Type of the visualization. Currently available: 'table'
    schema : dict
        Schema that describes the visualization, e.g. column names of a table
    algorithm_id : int
        Id of the algorithm
    """

    # fields
    name = Column(String)
    description = Column(String)
    type_ = Column("type", String)
    schema = Column(JSON)
    algorithm_id = Column(Integer, ForeignKey("algorithm.id"))

    # relationships
    algorithm = relationship("Algorithm", back_populates="ui_visualizations")
