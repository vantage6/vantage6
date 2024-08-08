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
    function_id : int
        Id of the function that the visualization is linked to
    function : Function
        Function that the visualization is linked to
    """

    # fields
    name = Column(String)
    description = Column(String)
    type_ = Column("type", String)
    schema = Column(JSON)
    function_id = Column(Integer, ForeignKey("function.id"))

    # relationships
    function = relationship("Function", back_populates="ui_visualizations")
