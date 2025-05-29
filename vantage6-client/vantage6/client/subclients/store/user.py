from typing import List
from vantage6.client.filter import post_filtering
from vantage6.common.client.client_base import ClientBase


class StoreUserSubClient(ClientBase.SubClient):
    """Subclient for the user registrations in the algorithm store."""

    @post_filtering(iterable=True)
    def list(
        self,
        username: str = None,
        role: int = None,
        page: int = 1,
        per_page: int = 10,
    ) -> List[dict]:
        """
        List algorithms

        Parameters
        ----------
        username : str, optional
            Filter by username (with LIKE operator).
        role : int, optional
            Filter by role id.
        field : str, optional
            Which data field to keep in the result. For instance, "field='username'"
            will only return the username of the registered users. Default is None.
        fields : list[str], optional
            Which data fields to keep in the result. For instance,
            "fields=['username', 'id']" will only return the username and id of the
            registered users. Default is None.
        filter_ : tuple, optional
            Filter the result on key-value pairs. For instance,
            "filter_=('username', 'my_username')" will only return the registered
            users with the username 'my_username'. Default is None.
        filters : list[tuple], optional
            Filter the result on multiple key-value pairs. For instance,
            "filters=[('username', 'my_username'), ('id', 1)]" will only return the
            registered users with the username 'my_username' and id 1. Default is None.
        page : int, optional
            Page number for pagination (default=1)
        per_page : int, optional
            Number of items per page (default=10)

        Returns
        -------
        list[dict]
            List of user registrations
        """
        params = {
            "username": username,
            "role_id": role,
            "page": page,
            "per_page": per_page,
        }
        return self.parent.request(
            "user",
            is_for_algorithm_store=True,
            params=params,
        )

    @post_filtering(iterable=False)
    def get(self, id_: int) -> dict:
        """
        Get a user registration by id

        Parameters
        ----------
        id_ : int
            The id of the user registration
        field : str, optional
            Which data field to keep in the result. For instance, "field='username'"
            will only return the username of the user. Default is None.
        fields : list[str], optional
            Which data fields to keep in the result. For instance,
            "fields=['username', 'id']" will only return the username and id of the
            user. Default is None.

        Returns
        -------
        dict
            The user
        """
        return self.parent.request(
            f"user/{id_}",
            is_for_algorithm_store=True,
        )

    @post_filtering(iterable=False)
    def register(self, username: str, roles: List[int]) -> dict:
        """
        Register a vantage6 user in this algorithm store.

        Parameters
        ----------
        username : str
            The username of the user
        roles : list[int]
            The roles of the user in this algorithm store
        field : str, optional
            Which data field to keep in the returned dict. For instance,
            "field='username'" will only return the username of the user. Default is
            None.
        fields : list[str], optional
            Which data fields to keep in the returned dict. For instance,
            "fields=['username', 'id']" will only return the username and id of the
            user. Default is None.

        Returns
        -------
        dict
            The user registration
        """
        data = {
            "username": username,
            "roles": roles,
        }
        return self.parent.request(
            "user",
            method="POST",
            is_for_algorithm_store=True,
            json=data,
        )

    @post_filtering(iterable=False)
    def update(self, id_: int, roles: List[int]) -> dict:
        """
        Update a user registration by id

        Parameters
        ----------
        id_ : int
            The id of the user registration
        roles : list[int]
            The new roles of the user in this algorithm store
        field : str, optional
            Which data field to keep in the returned dict. For instance,
            "field='username'" will only return the username of the user. Default is
            None.
        fields : list[str], optional
            Which data fields to keep in the returned dict. For instance,
            "fields=['username', 'id']" will only return the username and id of the
            user. Default is None.

        Returns
        -------
        dict
            The updated user registration
        """
        data = {
            "roles": roles,
        }
        return self.parent.request(
            f"user/{id_}",
            method="PATCH",
            is_for_algorithm_store=True,
            json=data,
        )

    def delete(self, id_: int) -> None:
        """
        Delete a user registration by id

        Parameters
        ----------
        id_ : int
            The id of the user registration
        """
        res = self.parent.request(
            f"user/{id_}",
            method="DELETE",
            is_for_algorithm_store=True,
        )
        self.parent.log.info(f"--> {res.get('msg')}")
