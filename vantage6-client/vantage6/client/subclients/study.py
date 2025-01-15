from typing import List
from vantage6.client.filter import post_filtering
from vantage6.common.client.client_base import ClientBase


class StudySubClient(ClientBase.SubClient):
    """Subclient for the algorithm store."""

    @post_filtering(iterable=False)
    def get(self, id_: int) -> dict:
        """
        Get a study by its id.

        Parameters
        ----------
        id_ : int
            The id of the study
        field: str, optional
            Which data field to keep in the result. For instance, "field='name'"
            will only return the name of the study. Default is None.
        fields: list[str], optional
            Which data fields to keep in the result. For instance,
            "fields=['name', 'id']" will only return the name and id of the
            study. Default is None.


        Returns
        -------
        dict
            The study
        """
        return self.parent.request(f"study/{id_}")

    @post_filtering()
    def list(
        self,
        name: str | None = None,
        organization: int | None = None,
        collaboration: int | None = None,
        include_organizations: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> List[dict]:
        """
        View your studies

        Parameters
        ----------
        name: str, optional (with LIKE operator)
            Filter studies by name
        organization: int, optional
            Filter studies by organization id
        collaboration: int, optional
            Filter studies by collaboration id
        include_organizations: bool, optional
            Include organizations in the response, by default False
        field: str, optional
            Which data field to keep in the result. For instance, "field='name'"
            will only return the name of the studies. Default is None.
        fields: list[str], optional
            Which data fields to keep in the result. For instance,
            "fields=['name', 'id']" will only return the name and id of the
            studies. Default is None.
        filter_: tuple, optional
            Filter the result on key-value pairs. For instance,
            "filter_=('name', 'study1')" will only return the studies with the name
            'study1'. Default is None.
        filters: list[tuple], optional
            Filter the result on multiple key-value pairs. For instance,
            "filters=[('name', 'study1'), ('id', 1)]" will only return the studies
            with the name 'study1' and id 1. Default is None.
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
        }
        if organization is not None:
            params["organization_id"] = organization
        if collaboration is not None:
            params["collaboration_id"] = collaboration
        if include_organizations:
            params["include"] = "organizations"
        return self.parent.request("study", params=params)

    @post_filtering(iterable=False)
    def create(
        self, name: str, organizations: List[int], collaboration: int = None
    ) -> dict:
        """
        Create new study

        Parameters
        ----------
        name : str
            Name of the study
        organizations : list[int]
            List of organization ids which participate in the study
        collaboration : int | None
            Id of the collaboration the study is part of. If None, the value of
            setup_collaboration() is used.
        field: str, optional
            Which data field to keep in the returned dict. For instance, "field='name'"
            will only return the name of the study. Default is None.
        fields: list[str], optional
            Which data fields to keep in the returned dict. For instance,
            "fields=['name', 'id']" will only return the name and id of the study.
            Default is None.

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

    def delete(self, id_: int = None) -> None:
        """Deletes a study

        Parameters
        ----------
        id_ : int
            Id of the study you want to delete
        """
        res = self.parent.request(f"study/{id_}", method="delete")
        self.parent.log.info(f"--> {res.get('msg')}")

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
        field: str, optional
            Which data field to keep in the returned dict. For instance, "field='name'"
            will only return the name of the study. Default is None.
        fields: list[str], optional
            Which data fields to keep in the returned dict. For instance,
            "fields=['name', 'id']" will only return the name and id of the study.
            Default is None.

        Returns
        -------
        dict
            Containing the updated study information
        """
        data = {"name": name, "organization_ids": organizations}
        data = self._clean_update_data(data)
        return self.parent.request(f"study/{id_}", method="patch", json=data)

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
