import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, select
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager
from vantage6.algorithm.store.model.common.enums import AlgorithmStatus, ReviewStatus


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
    code_url : str
        URL to the repository containing the code of this algorithm
    documentation_url : str
        URL to the documentation of this algorithm
    digest : str
        Hash digest of the algorithm
    submitted_at: datetime
        Date at which the algorithm was submitted
    approved_at: datetime
        Date at which the algorithm was approved
    invalidated_at: datetime
        Date at which the algorithm was rejected or replaced by a newer version
    developer_id : int
        ID of the user that developed the algorithm
    submission_comments : str
        Comments done by the developer to the submission of the algorithm

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
    status = Column(String, default=AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT.value)
    code_url = Column(String)
    documentation_url = Column(String)
    partitioning = Column(String)
    vantage6_version = Column(String)
    digest = Column(String)
    submitted_at = Column(
        DateTime, default=datetime.datetime.now(datetime.timezone.utc)
    )
    approved_at = Column(DateTime)
    invalidated_at = Column(DateTime)
    developer_id = Column(Integer, ForeignKey("user.id"))
    submission_comments = Column(String)

    # relationships
    functions = relationship("Function", back_populates="algorithm")
    developer = relationship("User", back_populates="algorithms")
    reviews = relationship("Review", back_populates="algorithm")

    def is_review_finished(self) -> bool:
        """
        Check if an algorithm is being reviewed.

        Returns
        -------
        bool
            True if the algorithm is being reviewed, False otherwise
        """
        return self.status not in [
            AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT,
            AlgorithmStatus.UNDER_REVIEW,
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

    def approve(self) -> None:
        """
        Approve the algorithm, and invalidate all other algorithms with the same image.
        """
        self.status = AlgorithmStatus.APPROVED.value
        self.approved_at = datetime.datetime.now(datetime.timezone.utc)
        self.save()

        for other_version in self.get_by_image(self.image):
            # skip the current version and versions that are not yet reviewed and
            # are newer (as in submitted later) than the current version
            if (
                not other_version.is_review_finished()
                and other_version.submitted_at > self.submitted_at
            ) or other_version.id == self.id:
                continue
            other_version.invalidated_at = self.approved_at
            other_version.status = AlgorithmStatus.REPLACED.value
            other_version.save()

    @classmethod
    def get_by_image(cls, image: str) -> list["Algorithm"]:
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
        result = session.scalars(
            select(cls).filter_by(image=image, invalidated_at=None)
        ).all()
        session.commit()
        return result

    @classmethod
    def get_by_algorithm_status(
        cls, state: AlgorithmStatus | list[AlgorithmStatus]
    ) -> list["Algorithm"]:
        """
        Get algorithms by one or more algorithm statuses.

        Parameters
        ----------
        state : AlgorithmStatus | list[AlgorithmStatus]
            One or more algorithm statuses

        Returns
        -------
        list[Algorithm]
            Algorithms with one of the given statuses
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalars(
            select(cls)
            .where(
                cls.status.in_(
                    [s.value for s in state] if isinstance(state, list) else state.value
                )
            )
            .order_by(cls.id)
        ).all()
        session.commit()
        return result
