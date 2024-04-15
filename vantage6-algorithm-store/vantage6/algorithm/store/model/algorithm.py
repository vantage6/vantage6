from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base


class Algorithm(Base):
    """
    Table that describes which algorithms are available.

    Attributes
    ----------
    name : str
        Name of the algorithm
    description: str
        Description of the algorithm
    image : str
        Docker image URL
    partitioning : str
        Type of partitioning
    vantage6_version : str
        Version of vantage6 that the algorithm is built with

    functions : list[:class:`~.model.function.function`]
        List of functions that are available in the algorithm
    developer : list[:class:`~.model.user.User`]
        List of users that have developed the algorithm
    review : :class:`~.model.review.Review`
        Review of the algorithm
    """

    # fields
    name = Column(String)
    description = Column(String)
    image = Column(String)
    # status = Column(String)
    # code_url = Column(String)
    # documentation_url = Column(String)
    partitioning = Column(String)
    vantage6_version = Column(String)

    # relationships
    functions = relationship("Function", back_populates="algorithm")
    developer = relationship(
        "User", back_populates="algorithms", secondary="developer_algorithm_association"
    )
    review = relationship("Review", back_populates="algorithm")
