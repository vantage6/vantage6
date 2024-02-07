from __future__ import annotations
from sqlalchemy import Column, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager


class Review(Base):
    """Collection of :class:`.~vantage6.algorithm.store.model.review.Review` permissions

    Attributes
    ----------
    name : str
        Name of the role
    description : str
        Description of the role
    organization_id : int
        Id of the organization this role belongs to
    rules : list[:class:`.~vantage6.server.model.rule.Rule`]
        List of rules that belong to this role
    organization : :class:`.~vantage6.server.model.organization.Organization`
        Organization this role belongs to
    users : list[:class:`.~vantage6.server.model.user.User`]
        List of users that belong to this role
    """

    # fields
    algorithm_id = Column(Integer, ForeignKey("algorithm.id"))
    reviewer_id = Column(Integer, ForeignKey("user.id"))
    status = Column(Text)

    # relationships
    reviewers = relationship("User", back_populates="reviews")

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
            f"reviewers: {self.reviewers}, "
            ">"
        )
