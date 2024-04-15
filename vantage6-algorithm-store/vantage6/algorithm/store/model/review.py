from __future__ import annotations
from sqlalchemy import Column, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base


class Review(Base):
    """Database table that describe algorithm reviews and their status

    Attributes
    ----------
    algorithm_id : int
        Id of the algorithm
    reviewer_id : int
        Id of the user appointed as reviewer
    status : str
        Review status
    reviewers : list[:class:`~.model.user.User`]
        List of users that have written reviews
    algorithm : :class:`~.model.algorithm.Algorithm`
        Algorithm that the review is linked to
    """

    # fields
    algorithm_id = Column(Integer, ForeignKey("algorithm.id"))
    reviewer_id = Column(Integer, ForeignKey("user.id"))
    status = Column(Text)

    # relationships
    reviewers = relationship("User", back_populates="reviews")
    algorithm = relationship("Algorithm", back_populates="review")

    def __repr__(self) -> str:
        """
        String representation of the review.

        Returns
        -------
        str
            String representation of the role
        """
        return (
            f"<Review "
            f"algorithm: {self.algorithm_id}, "
            f"status: {self.status}, "
            f"reviewer_id: {self.reviewer_id}, "
            ">"
        )
