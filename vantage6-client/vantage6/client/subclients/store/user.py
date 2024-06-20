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
        username : str
            Filter by username (with LIKE operator).
        role : int
            Filter by role id.
        page : int
            Page number for pagination (default=1)
        per_page : int
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
            headers=self.parent.util._get_server_url_header(),
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

        Returns
        -------
        dict
            The user
        """
        return self.parent.request(
            f"user/{id_}",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
        )

    def register(self, username: str, roles: List[int]) -> dict:
        """
        Register a vantage6 user in this algorithm store.

        Parameters
        ----------
        username : str
            The username of the user
        roles : list[int]
            The roles of the user in this algorithm store

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
            headers=self.parent.util._get_server_url_header(),
            json=data,
        )

    def update(self, id_: int, roles: List[int]) -> dict:
        """
        Update a user registration by id

        Parameters
        ----------
        id_ : int
            The id of the user registration
        roles : list[int]
            The new roles of the user in this algorithm store
        """
        data = {
            "roles": roles,
        }
        return self.parent.request(
            f"user/{id_}",
            method="PATCH",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
            json=data,
        )

    def delete(self, id_: int) -> dict:
        """
        Delete a user registration by id

        Parameters
        ----------
        id_ : int
            The id of the user registration
        """
        return self.parent.request(
            f"user/{id_}",
            method="DELETE",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
        )
