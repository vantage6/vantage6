from typing import Any, List
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
            params=params,
        )

    @post_filtering(iterable=False)
    def create(self, name: str, description: str, rules: List[int]) -> dict[str, Any]:
        """
        Create a new role

        Parameters
        ----------
        name : str
            Name of the role.
        description : str
            Description of the role.
        rules : list[int]
            List of rule IDs associated with the role.

        Returns
        -------
        dict
            The created role.
        """
        data = {
            "name": name,
            "description": description,
            "rules": rules,
        }
        return self.parent.request(
            "role",
            method="post",
            is_for_algorithm_store=True,
            json=data,
        )

    @post_filtering(iterable=False)
    def edit(
        self,
        role_id: int,
        name: str = None,
        description: str = None,
        rules: List[int] = None,
    ) -> dict[str, Any]:
        """
        Edit an existing role

        Parameters
        ----------
        role_id : int
            ID of the role to edit.
        name : str, optional
            New name of the role.
        description : str, optional
            New description of the role.
        rules : list[int], optional
            New list of rule IDs associated with the role.
            CAUTION! This will not *add* rules but replace them. If
            you remove rules from your own role you lose access. By
            default None

        Returns
        -------
        dict
            The updated role.
        """
        data = {}
        if name is not None:
            data["name"] = name
        if description is not None:
            data["description"] = description
        if rules is not None:
            data["rules"] = rules

        return self.parent.request(
            f"role/{role_id}",
            method="patch",
            is_for_algorithm_store=True,
            json=data,
        )

    def delete(self, role_id: int) -> None:
        """
        Delete an existing role

        Parameters
        ----------
        role_id : int
            ID of the role to delete.

        Returns
        -------
        None
        """
        self.parent.request(
            f"role/{role_id}",
            method="delete",
            is_for_algorithm_store=True,
        )
