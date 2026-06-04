from sqlalchemy import Column, String, select

from vantage6.common.enum import StorePolicies

from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager
from vantage6.algorithm.store.model.common.enums import DefaultStorePolicies
from vantage6.algorithm.store.model.user import User


class Policy(Base):
    """
    Table that describes the policies of this algorithm store.

    Attributes
    ----------
    key: str
        Key of the setting
    value: str
        Value of the setting
    """

    key = Column(String)
    value = Column(String)

    @classmethod
    def get_as_dict(cls) -> dict[str, str]:
        """
        Get the policies as a dictionary.

        Returns
        -------
        dict[str, str]
            Dictionary of policies
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalars(select(cls)).all()
        session.commit()
        return {r.key: r.value for r in result}

    @classmethod
    def get_minimum_reviewers(cls) -> int:
        """
        Get the minimum number of reviewers for approving the algorithms.

        Returns
        -------
        int
            Minimum number of reviewers
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalars(
            select(cls).filter_by(key=StorePolicies.MIN_REVIEWERS.value)
        ).one_or_none()
        session.commit()
        if result is None:
            return DefaultStorePolicies.MIN_REVIEWERS.value
        return int(result.value)

    @classmethod
    def is_developer_allowed_assign_review(cls):
        """
        Check if developers are allowed to assign reviews to their own algorithms.

        Returns
        -------
        bool
            True if developers are allowed to assign reviews to their own algorithms,
            False otherwise
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalars(
            select(cls).filter_by(key=StorePolicies.ASSIGN_REVIEW_OWN_ALGORITHM.value)
        ).one_or_none()
        session.commit()
        if result is None:
            return DefaultStorePolicies.ASSIGN_REVIEW_OWN_ALGORITHM.value
        return result.value.lower() == "true" or result.value == "1"

    @classmethod
    def get_minimum_reviewing_orgs(cls) -> int:
        """
        Get the minimum number of organizations that have to be involved in the review
        process.

        Returns
        -------
        int
            Minimum number of reviewers
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalars(
            select(cls).filter_by(key=StorePolicies.MIN_REVIEWING_ORGANIZATIONS.value)
        ).one_or_none()
        session.commit()
        if result is None:
            return int(DefaultStorePolicies.MIN_REVIEWING_ORGANIZATIONS.value)
        return int(result.value)

    @classmethod
    def search_user_in_policy(cls, user: User, policy: StorePolicies) -> bool:
        """
        Search a user in a policy where specific users are indicated.
        The users have to be saved in the policy with their username.

        Parameters
        ----------
        user : User
            User to search for
        policy : StorePolicies
            Member of StorePolicies enum

        Returns
        -------
        bool
            True if user is found in policy, False otherwise
        """

        session = DatabaseSessionManager.get_session()
        result = session.scalars(select(cls).filter_by(key=policy.value)).all()
        session.commit()

        if result is None or result == []:
            # if the policy has not been set, allow all users to review
            return True
        else:
            if not isinstance(result, list):
                result = [result]
            result = next(
                (r for r in result if r.value == user.username),
                None,
            )

        if result is None:
            return False
        return True
