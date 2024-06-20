from typing import List
from vantage6.client.filter import post_filtering
from vantage6.common.client.client_base import ClientBase


class StoreRoleSubClient(ClientBase.SubClient):
    """Subclient for the roles from the algorithm store."""

    @post_filtering(iterable=True)
    def list(
        self,
        name: str = None,
        description: str = None,
        user: int = None,
        page: int = 1,
        per_page: int = 10,
    ) -> List[dict]:
        """
        List algorithms

        Parameters
        ----------
        name : str
            Filter by name (with LIKE operator).
        description : str
            Filter by description (with LIKE operator).
        user : int
            Filter by user id.
        page : int
            Page number for pagination (default=1)
        per_page : int
            Number of items per page (default=10)

        Returns
        -------
        list[dict]
            List of roles
        """
        params = {
            "name": name,
            "description": description,
            "user_id": user,
            "page": page,
            "per_page": per_page,
        }
        return self.parent.request(
            "role",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
            params=params,
        )
