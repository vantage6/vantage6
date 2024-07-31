from vantage6.client import ClientBase
from vantage6.client.filter import post_filtering


class StudySubClient(ClientBase.SubClient):
    """Sub client for the algorithm store."""

    @post_filtering(iterable=False)
    def get(self, id_: int) -> dict:
        """
        Get a session by its ID

        Parameters
        ----------
        id_ : int
            The ID of the session

        Returns
        -------
        dict
            The session details
        """
        return self.parent.request(f"session/{id_}")

    @post_filtering()
    def list(
        self,
        name: str = None,
        user: int = None,
        collaboration: int = None,
        scope: str = None,
        page: int = 1,
        per_page: int = 20,
        sort: str = None,
    ):
        """
        List of sessions

        Parameters
        ----------
        name : str, optional
            Filter sessions by name
        user : int, optional
            Filter sessions by user ID
        collaboration : int, optional
            Filter sessions by collaboration ID, overrides the ``collaboration_id``
            of the client. In case both are not set, no filtering is applied.
        scope : str, optional
            Filter sessions by scope, possible values are ``global``, ``collaboration``,
            ``organization`` and ``own``.
        page : int, optional
            Pagination page
        per_page : int, optional
            Number of items on a single page
        sort : str, optional
            Sort the result by this field. Adding a minus sign in front of the field
            will sort in descending order.

        Returns
        -------
        list[dict]
            Containing session information
        """
        params = {
            "name": name,
            "user_id": user,
            "collaboration_id": collaboration or self.collaboration_id,
            "scope": scope,
            "sort": sort,
            "page": page,
            "per_page": per_page,
        }

        return self.parent.request("session", params=params)

    @post_filtering(iterable=False)
    def update(self, id_: int, name: str = None, scope: str = None):
        """
        Modify a session

        This will update the session with the given ID. Only the fields that are
        provided will be updated.

        Parameters
        ----------
        id_ : int
            The ID of the session
        name : str, optional
            The new name of the session
        scope : str, optional
            The new scope of the session. Possible values are ``global``,
            ``collaboration``, ``organization`` and ``own``.

        Returns
        -------
        dict
            The updated session
        """
        return self.parent.request(
            f"session/{id_}",
            method="patch",
            json={"name": name, "scope": scope},
        )

    @post_filtering(iterable=False)
    def create(
        self,
        name: str = None,
        collaboration: int = None,
        study: int = None,
        scope: str = None,
    ):
        """
        Create a new session

        This will create an empty session. The session can be populated with one or
        more dataframes.

        Parameters
        ----------
        name: str, optional
            The name of the session
        collaboration: int, optional
            The collaboration ID of the session. In case this is not set, the
            collaboration ID of the client is used. When neither is set, the study ID
            needs to be provided.
        study: int, optional
            The study ID of the session. In case this is set, the data frames in this
            session will be scoped to the study.
        scope: str
            The scope of the session. Possible values are ``global``, ``collaboration``,
            ``organization`` and ``own``.

        Returns
        -------
        dict
            The created session
        """
        return self.parent.request(
            "session",
            method="post",
            json={
                "name": name,
                "collaboration_id": collaboration or self.collaboration_id,
                "study_id": study,
                "scope": scope,
            },
        )

    @post_filtering(iterable=False)
    def delete(self, id_: int, delete_dependents: bool = False):
        """
        Deletes a session

        Parameters
        ----------
        id_ : int
            Id of the session you want to delete
        delete_dependents : bool, optional
            Delete all dependent tasks and dataframes of the session as well. This
            includes tasks dataframes.
        """
        return self.parent.request(
            f"session/{id_}",
            method="delete",
            json={"delete_dependents": delete_dependents},
        )
