from vantage6.client.filter import post_filtering
from vantage6.client.subclients.store.review import ReviewSubClient
from vantage6.client.subclients.store.role import StoreRoleSubClient
from vantage6.client.subclients.store.rule import StoreRuleSubClient
from vantage6.client.subclients.store.user import StoreUserSubClient
from vantage6.client.subclients.store.policy import PolicySubClient
from vantage6.common.client.client_base import ClientBase


class AlgorithmStoreSubClient(ClientBase.SubClient):
    """Subclient for the algorithm store."""

    def __init__(self, parent: ClientBase):
        super().__init__(parent)
        self.url = None
        self.store_id = None

        self.base_client = self.parent

        self.role = StoreRoleSubClient(self)
        self.rule = StoreRuleSubClient(self)
        self.user = StoreUserSubClient(self)
        self.policy = PolicySubClient(self)
        self.review = ReviewSubClient(self)

    def set(self, id_: int) -> dict:
        """ "
        Set the algorithm store to use for the client.

        Parameters
        ----------
        id_ : int
            The id of the algorithm store.

        Returns
        -------
        dict
            The algorithm store.
        """
        store = self.get(id_)
        try:
            self.url = f"{store['url']}/api"
            self.store_id = id_
        except KeyError:
            self.parent.log.error("Algorithm store URL could not be set.")
        return store

    @post_filtering(iterable=False)
    def get(self, id_: int) -> dict:
        """Get an algorithm store by its id.

        Parameters
        ----------
        id_ : int
            The id of the algorithm store.
        field : str, optional
            Which data field to keep in the result. For instance, "field='name'"
            will only return the name of the algorithm store. Default is None.
        fields : list[str], optional
            Which data fields to keep in the result. For instance,
            "fields=['name', 'id']" will only return the name and id of the
            algorithm store. Default is None.

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
        field : str, optional
            Which data field to keep in the result. For instance, "field='name'"
            will only return the name of the algorithm stores. Default is None.
        fields : list[str], optional
            Which data fields to keep in the result. For instance,
            "fields=['name', 'id']" will only return the name and id of the
            algorithm stores. Default is None.
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
        collaboration: int | None = None,
        all_collaborations: bool = False,
        force: bool = False,
    ) -> dict:
        """
        Link an algorithm store to one or more collaborations.

        Parameters
        ----------
        algorithm_store_url : str
            The url of the algorithm store, including the API path.
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
        field : str, optional
            Which data field to keep in the returned dict. For instance, "field='name'"
            will only return the name of the algorithm store. Default is None.
        fields : list[str], optional
            Which data fields to keep in the returned dict. For instance,
            "fields=['name', 'id']" will only return the name and id of the algorithm
            store. Default is None.

        Returns
        -------
        dict
            The algorithm store.
        """
        if all_collaborations:
            collaboration = None
        elif collaboration is None and self.parent.collaboration_id is not None:
            collaboration = self.parent.collaboration_id
        elif collaboration is None:
            self.parent.log.error(
                "No collaboration given and default collaboration is not set. "
                "Please provide a collaboration, set a default collaboration, or make "
                "the algorithm store available to all collaborations with "
                "all_collaborations=True."
            )
            return
        data = {
            "algorithm_store_url": algorithm_store_url,
            "name": name,
            "force": force,
            "server_url": self.parent.base_path,
        }
        if collaboration is not None:
            data["collaboration_id"] = (collaboration,)
        return self.parent.request("algorithmstore", method="post", json=data)

    @post_filtering(iterable=False)
    def update(
        self,
        id_: int = None,
        name: str = None,
        collaboration: int = None,
        all_collaborations: bool = None,
    ) -> dict:
        """Update an algorithm store.

        Parameters
        ----------
        id_ : int
            The id of the algorithm store. If not given, the algorithm store must be
            set with client.store.set().
        name : str, optional
            The name of the algorithm store.
        collaboration : int, optional
            The id of the collaboration to link the algorithm store to.
        all_collaborations : bool, optional
            If True, the algorithm store is linked to all collaborations. If False,
            the collaboration_id must be given.
        field : str, optional
            Which data field to keep in the returned dict. For instance, "field='name'"
            will only return the name of the algorithm store. Default is None.
        fields : list[str], optional
            Which data fields to keep in the returned dict. For instance,
            "fields=['name', 'id']" will only return the name and id of the algorithm
            store. Default is None.

        Returns
        -------
        dict
            The updated algorithm store.
        """
        id_ = self.__get_store_id(id_)
        if id_ is None:
            return
        data = {}
        if name is not None:
            data["name"] = name
        if collaboration is not None or all_collaborations:
            data["collaboration_id"] = collaboration
        return self.parent.request(f"algorithmstore/{id_}", method="patch", json=data)

    def delete(self, id_: int = None) -> None:
        """Delete an algorithm store.

        Parameters
        ----------
        id_ : int
            The id of the algorithm store. If not given, the algorithm store must be
            set with client.store.set().
        """
        id_ = self.__get_store_id(id_)
        if id_ is None:
            return
        res = self.parent.request(
            f"algorithmstore/{id_}",
            method="delete",
            params={
                "server_url": self.parent.base_path,
            },
        )
        self.parent.log.info(f"--> {res.get('msg')}")

    def __get_store_id(self, id_: int = None) -> int:
        """
        Get the algorithm store id.

        Parameters
        ----------
        id_ : int
            The id of the algorithm store. If not given, the algorithm store must be
            set with client.store.set().

        Returns
        -------
        int
            The algorithm store id.
        """
        if id_ is None:
            id_ = self.store_id
            if id_ is None:
                self.parent.log.error("No algorithm store id given or set.")
                return
        return id_
