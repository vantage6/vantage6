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
        user_id: int = None,
        current_user: bool = False,
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
        user_id : int, optional
            Filter by user using the user id. If provided together with current_user,
            the current user will be used and user_id will be ignored.
        current_user : bool, optional
            Filter rules for the current user.
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
            "current_user": current_user,
            "page": page,
            "per_page": per_page,
        }
        if user_id:
            params["user_id"] = user_id

        return self.parent.request(
            "rule",
            is_for_algorithm_store=True,
            params=params,
        )
