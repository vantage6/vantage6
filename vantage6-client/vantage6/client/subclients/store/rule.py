from typing import List
from vantage6.client.filter import post_filtering
from vantage6.common.client.client_base import ClientBase


class StoreRuleSubClient(ClientBase.SubClient):
    """Subclient for the rules from the algorithm store."""

    @post_filtering(iterable=True)
    def list(
        self,
        name: str = None,
        operation: str = None,
        role: int = None,
        username: str = None,
        serverUrl: str = None,
        page: int = 1,
        per_page: int = 10,
    ) -> List[dict]:
        """
        List algorithms

        Parameters
        ----------
        name : str, optional
            Filter by name (with LIKE operator).
        operation : str, optional
            Filter by operation (view, create, update, delete, or review).
        role : int, optional
            Filter by role id.
        username : str, optional
            Filter by user using the username. Used in combination with 'serverUrl' to
            identify a user.
        serverUrl : str, optional
            Filter by user. Used in combination with 'username' to identify a user. If
            not given, defaults to the server this client is connected to.
        field : str, optional
            Which data field to keep in the result. For instance, "field='name'"
            will only return the name of the rules. Default is None.
        fields : list[str]
            Which data fields to keep in the result. For instance,
            "fields=['name', 'id']" will only return the name and id of the
            rules. Default is None.
        filter_ : tuple[str, str], optional
            Filter the result on key-value pairs. For instance,
            "filter_=('name', 'my_name')" will only return the rules with the
            name 'my_name'. Default is None.
        filters : list[tuple[str, str]], optional
            Filter the result on multiple key-value pairs. For instance,
            "filters=[('name', 'my_name'), ('id', 1)]" will only return the
            rules with the name 'my_name' and id 1. Default is None.
        page : int, optional
            Page number for pagination (default=1)
        per_page : int, optional
            Number of items per page (default=10)

        Returns
        -------
        list[dict]
            List of rules
        """
        params = {
            "name": name,
            "operation": operation,
            "role_id": role,
            "page": page,
            "per_page": per_page,
        }
        if username:
            params["username"] = username
            params["server_url"] = serverUrl or self.parent.base_path

        return self.parent.request(
            "rule",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
            params=params,
        )
