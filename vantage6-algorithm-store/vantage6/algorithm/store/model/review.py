from __future__ import annotations
from sqlalchemy import Column, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base
from vantage6.algorithm.store.model.common.enums import ReviewStatus


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
    comment : str
        Reviewer's comment
    reviewers : list[:class:`~.model.user.User`]
        List of users that have written reviews
    algorithm : :class:`~.model.algorithm.Algorithm`
        Algorithm that the review is linked to
    """

    # fields
    algorithm_id = Column(Integer, ForeignKey("algorithm.id"))
    reviewer_id = Column(Integer, ForeignKey("user.id"))
    status = Column(Text, default=ReviewStatus.UNDER_REVIEW.value)
    comment = Column(Text)

    # relationships
    reviewer = relationship("User", back_populates="reviews")
    algorithm = relationship("Algorithm", back_populates="reviews")

    def is_review_finished(self) -> bool:
        """
        Check if the review is finished.

        Returns
        -------
        bool
            True if the review is finished, False otherwise
        """
        return self.status != ReviewStatus.UNDER_REVIEW

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
