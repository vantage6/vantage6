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
        name : str, optional
            Filter by name (with LIKE operator).
        description : str, optional
            Filter by description (with LIKE operator).
        user : int, optional
            Filter by user id.
        field : str, optional
            Which data field to keep in the result. For instance, "field='name'"
            will only return the name of the roles. Default is None.
        fields : list[str], optional
            Which data fields to keep in the result. For instance,
            "fields=['name', 'id']" will only return the name and id of the
            roles. Default is None.
        filter_ : tuple, optional
            Filter the result on key-value pairs. For instance,
            "filter_=('name', 'my_name')" will only return the roles with the
            name 'my_name'. Default is None.
        filters : list[tuple], optional
            Filter the result on multiple key-value pairs. For instance,
            "filters=[('name', 'my_name'), ('id', 1)]" will only return the
            roles with the name 'my_name' and id 1. Default is None.
        page : int, optional
            Page number for pagination (default=1)
        per_page : int, optional
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
