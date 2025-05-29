from typing import List
from vantage6.client.filter import post_filtering
from vantage6.common.client.client_base import ClientBase


class ReviewSubClient(ClientBase.SubClient):
    """Subclient for the reviews from the algorithm store."""

    @post_filtering(iterable=True)
    def list(
        self,
        algorithm: int = None,
        reviewer: int = None,
        under_review: bool = None,
        reviewed: bool = None,
        approved: bool = None,
        rejected: bool = None,
        page: int = 1,
        per_page: int = 10,
    ) -> List[dict]:
        """
        List reviews

        Parameters
        ----------
        algorithm : int, optional
            Filter by algorithm id.
        reviewer : int, optional
            Filter by user id of the reviewer.
        under_review : bool, optional
            Filter by under review status.
        reviewed : bool, optional
            Filter by reviewed (either approve or rejected).
        approved : bool, optional
            Filter by approved status.
        rejected : bool, optional
            Filter by rejected status.
        field : str, optinal
            Which data field to keep in the result. For instance, "field='name'"
            will only return the name of the reviews. Default is None.
        fields : list[str], optional
            Which data fields to keep in the result. For instance,
            "fields=['name', 'id']" will only return the name and id of the
            reviews. Default is None.
        filter_ : tuple, optional
            Filter the result on key-value pairs. For instance,
            "filter_=('name', 'my_name')" will only return the reviews with the
            name 'my_name'. Default is None.
        filters : list[tuple], optional
            Filter the result on multiple key-value pairs. For instance,
            "filters=[('name', 'my_name'), ('id', 1)]" will only return the
            reviews with the name 'my_name' and id 1. Default is None.
        page : int, optional
            Page number for pagination (default=1)
        per_page : int, optional
            Number of items per page (default=10)

        Returns
        -------
        list[dict]
            List of reviews
        """
        params = {
            "algorithm_id": algorithm,
            "reviewer_id": reviewer,
            "page": page,
            "per_page": per_page,
        }
        if under_review is not None:
            params["under_review"] = under_review
        if reviewed is not None:
            params["reviewed"] = reviewed
        if approved is not None:
            params["approved"] = approved
        if rejected is not None:
            params["rejected"] = rejected
        return self.parent.request(
            "review",
            is_for_algorithm_store=True,
            params=params,
        )

    @post_filtering(iterable=False)
    def get(self, id_: int) -> dict:
        """
        Get a review by its id.

        Parameters
        ----------
        id_ : int
            The id of the review.
        field : str, optional
            Which data field to keep in the result. For instance, "field='name'"
            will only return the name of the review. Default is None.
        fields : list[str], optional
            Which data fields to keep in the result. For instance,
            "fields=['name', 'id']" will only return the name and id of the
            review. Default is None.

        Returns
        -------
        dict
            The review.
        """
        return self.parent.request(
            f"review/{id_}",
            is_for_algorithm_store=True,
        )

    @post_filtering(iterable=False)
    def create(self, algorithm: int, reviewer: int) -> dict:
        """
        Assign an algorithm to be reviewed by a particular user.

        Parameters
        ----------
        algorithm : int
            The id of the algorithm.
        reviewer : int
            The user id for the reviewer.
        field : str, optional
            Which data field to keep in the returned dict. For instance, "field='name'"
            will only return the name of the review. Default is None.
        fields : list[str], optional
            Which data fields to keep in the returned dict. For instance,
            "fields=['name', 'id']" will only return the name and id of the review.
            Default is None.

        Returns
        -------
        dict
            The created review.
        """
        return self.parent.request(
            "review",
            method="post",
            is_for_algorithm_store=True,
            json={"algorithm_id": algorithm, "reviewer_id": reviewer},
        )

    def delete(self, id_: int) -> None:
        """
        Delete a review.

        Parameters
        ----------
        id_ : int
            The id of the review.
        """
        res = self.parent.request(
            f"review/{id_}",
            method="delete",
            is_for_algorithm_store=True,
        )
        self.parent.log.info(f"--> {res.get('msg')}")

    def approve(self, id_: int, comment: str = None) -> dict:
        """
        Approve a review.

        Parameters
        ----------
        id_ : int
            The id of the review.
        comment : str
            A comment for the approval of the review. Optional.

        Returns
        -------
        dict
            The approved review.
        """
        body = {}
        if comment:
            body["comment"] = comment
        return self.parent.request(
            f"review/{id_}/approve",
            method="post",
            is_for_algorithm_store=True,
            json=body,
        )

    def reject(self, id_: int, comment: str = None) -> dict:
        """
        Reject a review.

        Parameters
        ----------
        id_ : int
            The id of the review.
        comment : str
            A comment for the rejection of the review. Optional.

        Returns
        -------
        dict
            The rejected review.
        """
        body = {}
        if comment:
            body["comment"] = comment
        return self.parent.request(
            f"review/{id_}/reject",
            method="post",
            is_for_algorithm_store=True,
            json=body,
        )
