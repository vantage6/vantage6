from typing import List
from vantage6.client.filter import post_filtering
from vantage6.common.client.client_base import ClientBase


class StudySubClient(ClientBase.SubClient):
    """Subclient for the algorithm store."""

    @post_filtering(iterable=False)
    def get(self, id_: int) -> dict:
        """Get a study by its id.

        Parameters
        ----------
        id_ : int
            The id of the study

        Returns
        -------
        dict
            The study
        """
        return self.parent.request(f"study/{id_}")

    @post_filtering()
    def list(
        self,
        name: str = None,
        organization: int = None,
        include_organizations: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> List[dict]:
        """View your studies

        Parameters
        ----------
        name: str, optional (with LIKE operator)
            Filter studies by name
        organization: int, optional
            Filter studies by organization id
        include_organizations: bool, optional
            Include organizations in the response, by default False
        page: int, optional
            Pagination page, by default 1
        per_page: int, optional
            Number of items on a single page, by default 20

        Returns
        -------
        list[dict]
            Containing collabotation information
        """
        params = {
            "page": page,
            "per_page": per_page,
            "name": name,
            "organization_id": organization,
        }
        if include_organizations:
            params["include"] = "organizations"
        return self.parent.request("study", params=params)

    @post_filtering(iterable=False)
    def create(
        self, name: str, organizations: List[int], collaboration: int = None
    ) -> dict:
        """Create new study

        Parameters
        ----------
        name : str
            Name of the study
        organizations : list[int]
            List of organization ids which participate in the study
        collaboration : int | None
            Id of the collaboration the study is part of. If None, the value of
            setup_collaboration() is used.

        Returns
        -------
        dict
            Containing the new study information
        """
        if collaboration is None:
            collaboration = self.parent.collaboration_id
            if not collaboration:
                raise ValueError(
                    "No collaboration id provided. Please provide the collaboration as "
                    "argument or use `client.setup_collaboration`."
                )
        return self.parent.request(
            "study",
            method="post",
            json={
                "name": name,
                "organization_ids": organizations,
                "collaboration_id": collaboration,
            },
        )

    @post_filtering(iterable=False)
    def delete(self, id_: int = None) -> dict:
        """Deletes a study

        Parameters
        ----------
        id_ : int
            Id of the study you want to delete

        Returns
        -------
        dict
            Message from the server
        """
        return self.parent.request(f"study/{id_}", method="delete")

    @post_filtering(iterable=False)
    def update(
        self,
        id_: int,
        name: str = None,
        organizations: List[int] = None,
    ) -> dict:
        """
        Update study information

        Parameters
        ----------
        id_ : int
            Id of the study you want to update.
        name : str, optional
            New name of the study
        organizations : list[int], optional
            New list of organization ids which participate in the study

        Returns
        -------
        dict
            Containing the updated study information
        """
        json_data = {}
        if name:
            json_data["name"] = name
        if organizations:
            json_data["organization_ids"] = organizations
        return self.parent.request(f"study/{id_}", method="patch", json=json_data)

    def add_organization(self, organization: int, study: int = None) -> List[dict]:
        """
        Add an organization to a study

        Parameters
        ----------
        organization : int
            Id of the organization you want to add to the study
        study : int, optional
            Id of the study you want to add the organization to.

        Returns
        -------
        list[dict]
            Containing the updated list of organizations in the study
        """
        return self.parent.request(
            f"study/{study}/organization",
            method="post",
            json={"id": organization},
        )

    def remove_organization(self, organization: int, study: int = None) -> List[dict]:
        """
        Remove an organization from a study

        Parameters
        ----------
        organization : int
            Id of the organization you want to remove from the study
        study : int, optional
            Id of the study you want to remove the organization from

        Returns
        -------
        list[dict]
            Containing the updated list of organizations in the study
        """
        return self.parent.request(
            f"study/{study}/organization",
            method="delete",
            json={"id": organization},
        )
