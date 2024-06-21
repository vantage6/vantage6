import datetime
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound


from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager
from vantage6.algorithm.store.model.common.enums import ReviewStatus


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
    status: str
        Review status of the algorithm
    submitted_at: datetime
        Date at which the algorithm was submitted
    approved_at: datetime
        Date at which the algorithm was approved
    invalidated_at: datetime
        Date at which the algorithm was rejected or replaced by a newer version

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
    status = Column(String, default=ReviewStatus.AWAITING_REVIEWER_ASSIGNMENT.value)
    # code_url = Column(String)
    # documentation_url = Column(String)
    partitioning = Column(String)
    vantage6_version = Column(String)
    submitted_at = Column(
        DateTime, default=datetime.datetime.now(datetime.timezone.utc)
    )
    approved_at = Column(DateTime)
    invalidated_at = Column(DateTime)
    developer_id = Column(Integer, ForeignKey("user.id"))

    # relationships
    functions = relationship("Function", back_populates="algorithm")
    developer = relationship("User", back_populates="algorithms")
    reviews = relationship("Review", back_populates="algorithm")

    def is_review_finished(self) -> bool:
        """
        Check if an algorithm is being reviewed.
        """
        return self.status in [
            ReviewStatus.APPROVED,
            ReviewStatus.REJECTED,
        ]

    def are_all_reviews_approved(self) -> bool:
        """
        Check if all reviews are approved.

        Returns
        -------
        bool
            True if all reviews are approved, False otherwise
        """
        return all([review.status == ReviewStatus.APPROVED for review in self.reviews])

    @classmethod
    def get_by_image(cls, image: str) -> "Algorithm":
        """
        Get an algorithm by image.

        Parameters
        ----------
        image : str
            Docker image URL

        Returns
        -------
        list[Algorithm]
            Algorithms with the given image that are not invalidated
        """
        session = DatabaseSessionManager.get_session()
        result = session.query(cls).filter_by(image=image, invalidated_at=None).all()
        session.commit()
        return result
