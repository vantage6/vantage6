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
        algorithm : int
            Filter by algorithm id.
        reviewer : int
            Filter by user id of the reviewer.
        under_review : bool
            Filter by under review status.
        reviewed : bool
            Filter by reviewed (either approve or rejected).
        approved : bool
            Filter by approved status.
        rejected : bool
            Filter by rejected status.
        page : int
            Page number for pagination (default=1)
        per_page : int
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
            headers=self.parent.util._get_server_url_header(),
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

        Returns
        -------
        dict
            The review.
        """
        return self.parent.request(
            f"review/{id_}",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
        )

    def create(self, algorithm: int, reviewer: int) -> dict:
        """
        Assign an algorithm to be reviewed by a particular user.

        Parameters
        ----------
        algorithm : int
            The id of the algorithm.
        reviewer : int
            The user id for the reviewer.

        Returns
        -------
        dict
            The created review.
        """
        return self.parent.request(
            "review",
            method="post",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
            json={"algorithm_id": algorithm, "reviewer_id": reviewer},
        )

    def delete(self, id_: int) -> dict:
        """
        Delete a review.

        Parameters
        ----------
        id_ : int
            The id of the review.

        Returns
        -------
        dict
            The deleted review.
        """
        return self.parent.request(
            f"review/{id_}",
            method="delete",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
        )

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
            headers=self.parent.util._get_server_url_header(),
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
            headers=self.parent.util._get_server_url_header(),
            json=body,
        )
