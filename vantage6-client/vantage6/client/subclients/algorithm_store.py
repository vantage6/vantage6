from vantage6.client.filter import post_filtering
from vantage6.common.client.client_base import ClientBase


class AlgorithmStoreSubClient(ClientBase.SubClient):
    """Subclient for the algorithm store."""

    @post_filtering(iterable=False)
    def get(self, id_: int) -> dict:
        """Get an algorithm store by its id.

        Parameters
        ----------
        id_ : int
            The id of the algorithm store.

        Returns
        -------
        dict
            The algorithm store.
        """
        return self.parent.request(f"algorithmstore/{id_}")

    @post_filtering(iterable=True)
    def list(
        self,
        name: str = None,
        url: str = None,
        collaboration: int = None,
        page: int = 1,
        per_page: int = 10,
    ) -> list[dict]:
        """List all algorithm stores.

        Parameters
        ----------
        name : str, optional
            Filter by name (with LIKE operator)
        url : str, optional
            Filter by algorithm store url (with LIKE operator)
        collaboration : int, optional
            Filter by collaboration id. If not given and client.setup_collaboration()
            was called, the collaboration id from the setup is used. Otherwise, all
            algorithm stores are returned.
        page : int, optional
            The page number to retrieve.
        per_page : int, optional
            The number of items to retrieve per page.

        Returns
        -------
        list[dict]
            The algorithm stores.
        """
        if collaboration is None:
            collaboration = self.parent.collaboration_id
        params = {
            "name": name,
            "url": url,
            "collaboration_id": collaboration,
            "page": page,
            "per_page": per_page,
        }
        return self.parent.request("algorithmstore", params=params)

    @post_filtering(iterable=False)
    def create(
        self,
        algorithm_store_url: str,
        name: str,
        collaboration: int = None,
        all_collaborations: bool = False,
        force: bool = False,
    ) -> dict:
        """
        Link an algorithm store to one or more collaborations.

        Parameters
        ----------
        algorithm_store_url : str
            The url of the algorithm store.
        name : str
            The name of the algorithm store.
        collaboration : int, optional
            The id of the collaboration to link the algorithm store to. If not given
            and client.setup_collaboration() was called, the collaboration id from the
            setup is used. If neither is the case, all_collaborations must be set to
            True explicitly.
        all_collaborations : bool, optional
            If True, the algorithm store is linked to all collaborations. If False,
            the collaboration_id must be given.
        force : bool, optional
            If True, the algorithm store will be linked to the collaboration even for
            localhost urls - which is not recommended in production scenarios for
            security reasons.
        """
        if collaboration is None:
            collaboration = self.parent.collaboration_id
        if all_collaborations:
            collaboration = None
        elif collaboration is None:
            raise ValueError(
                "No collaboration given and default collaboration is not set. "
                "Please provide a collaboration, set a default collaboration, or make "
                "the algorithm store available to all collaborations with "
                "all_collaborations=True."
            )
        data = {
            "algorithm_store_url": algorithm_store_url,
            "name": name,
            "collaboration_id": collaboration,
            "all_collaborations": all_collaborations,
            "force": force,
            "server_url": f"{self.parent.host}/{self.parent.path}",
        }
        return self.parent.request("algorithmstore", method="post", data=data)

    def update(
        self,
        id_: int,
        name: str = None,
        collaboration: int = None,
        all_collaborations: bool = None,
    ):
        """Update an algorithm store.

        Parameters
        ----------
        id_ : int
            The id of the algorithm store.
        name : str, optional
            The name of the algorithm store.
        collaboration : int, optional
            The id of the collaboration to link the algorithm store to.
        all_collaborations : bool, optional
            If True, the algorithm store is linked to all collaborations. If False,
            the collaboration_id must be given.
        """
        data = {
            "name": name,
        }
        if collaboration is not None or all_collaborations:
            data["collaboration_id"] = collaboration
        return self.parent.request(f"algorithmstore/{id_}", method="patch", data=data)

    def delete(self, id_: int):
        """Delete an algorithm store.

        Parameters
        ----------
        id_ : int
            The id of the algorithm store.
        """
        return self.parent.request(f"algorithmstore/{id_}", method="delete")
