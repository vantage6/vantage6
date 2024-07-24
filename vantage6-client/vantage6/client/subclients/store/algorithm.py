from typing import List
from vantage6.client.filter import post_filtering
from vantage6.common.client.client_base import ClientBase


class AlgorithmSubClient(ClientBase.SubClient):
    """Subclient for the algorithms from the algorithm store."""

    @post_filtering(iterable=False)
    def get(self, id_: int) -> dict:
        """Get an algorithm by its id.

        Parameters
        ----------
        id_ : int
            The id of the algorithm.

        Returns
        -------
        dict
            The algorithm.
        """
        return self.parent.request(
            f"algorithm/{id_}",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
        )

    @post_filtering(iterable=True)
    def list(
        self,
        name: str = None,
        description: str = None,
        image: str = None,
        partitioning: str = None,
        v6_version: str = None,
        awaiting_reviewer_assignment: bool = None,
        under_review: bool = None,
        in_review_process: bool = None,
        invalidated: bool = None,
    ) -> list[dict]:
        """
        List algorithms.

        By default, only approved algorithms are returned.

        Parameters
        ----------
        name : str
            Filter by name (with LIKE operator).
        description : str
            Filter by description (with LIKE operator).
        image : str
            Filter by image (with LIKE operator).
        partitioning : str
            Filter by partitioning (horizontal or vertical).
        v6_version : str
            Filter by version (with LIKE operator).
        awaiting_reviewer_assignment : bool
            Filter by whether the algorithm is awaiting reviewer assignment.
        under_review: bool
            Filter by whether the algorithm is under review.
        in_review_process : bool
            Filter by whether the algorithm is in the review process, i.e. either
            awaiting reviewer assignment or under review.
        invalidated : bool
            Filter by whether the algorithm is invalidated.

        Returns
        -------
        list[dict]
            List of algorithms
        """
        params = {
            "name": name,
            "description": description,
            "image": image,
            "partitioning": partitioning,
            "v6_version": v6_version,
        }
        if awaiting_reviewer_assignment is not None:
            params["awaiting_reviewer_assignment"] = awaiting_reviewer_assignment
        if under_review is not None:
            params["under_review"] = under_review
        if in_review_process is not None:
            params["in_review_process"] = in_review_process
        if invalidated is not None:
            params["invalidated"] = invalidated
        return self.parent.request(
            "algorithm",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
            params=params,
        )

    @post_filtering(iterable=False)
    def create(
        self,
        name: str,
        description: str,
        image: str,
        partitioning: str,
        vantage6_version: str,
        code_url: str,
        functions: List[dict],
        documentation_url: str = None,
    ) -> dict:
        """
        Add an algorithm to the algorithm store

        Parameters
        ----------
        name : str
            Name of the algorithm
        description : str
            Description of the algorithm
        image : str
            Docker image of the algorithm
        partitioning : str
            Partitioning of the algorithm (horizontal or vertical)
        vantage6_version : str
            Vantage6 version of the algorithm
        code_url : str
            URL to the repository containing the algorithm code
        functions : list[dict]
            List of functions of the algorithm. Each function is a dict with
            the following keys:
            - name: str
                Name of the function
            - description: str, optional
                Description of the function
            - type: string
                Type of the function (central or federated)
            - databases: list[dict]
                List of databases of the function. Each database is a dict with
                the following keys:
                - name: str
                    Name of the database
                - description: str, optional
                    Description of the database
            - arguments: list[dict]
                List of arguments of the function. Each argument is a dict with
                the following keys:
                - name: str
                    Name of the argument
                - description: str, optional
                    Description of the argument
                - type: str
                    Type of the argument. Can be 'string', 'integer', 'float',
                    'boolean', 'json', 'column', 'organization' or 'organizations'
            - ui_visualizations: list[dict]
                List of UI visualizations of the function. Each visualization
                is a dict with the following keys:
                - name: str
                    Name of the visualization
                - description: str, optional
                    Description of the visualization
                - type: str
                    Type of the visualization. Can be 'table'
                - schema: dict, optional
                    Visualization details. For example, for a table, the schema
                    could be a dict with the following keys:
                    - location: list[str]
                        Where data to be visualized are stored in the results. For
                        example, if the data is stored in the 'data' key of the
                        results, the location would be ['data'].
                    - columns: list[str]
                        List of column names to visualize
        documentation_url : str, optional
            URL to the documentation of the algorithm


        Returns
        -------
        dict
            The created algorithm
        """
        body = {
            "name": name,
            "image": image,
            "partitioning": partitioning,
            "vantage6_version": vantage6_version,
            "functions": functions,
            "description": description,
            "code_url": code_url,
        }
        if documentation_url:
            body["documentation_url"] = documentation_url
        return self.parent.request(
            "algorithm",
            method="post",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
            json=body,
        )

    def delete(self, id_: int) -> dict:
        """
        Delete an algorithm from the algorithm store

        Parameters
        ----------
        id_ : int
            Id of the algorithm

        Returns
        -------
        dict
            The deleted algorithm
        """
        return self.parent.request(
            f"algorithm/{id_}",
            method="delete",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
        )

    def invalidate(self, id_: int) -> dict:
        """
        Invalidate an algorithm in the algorithm store. An invalidated algorithm
        is marked as outdated but is not deleted - you can therefore still view it
        and link that to the results of executed analyses.

        Parameters
        ----------
        id_ : int
            Id of the algorithm

        Returns
        -------
        dict
            The invalidated algorithm
        """
        return self.parent.request(
            f"algorithm/{id_}/invalidate",
            method="post",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
        )

    def update(
        self,
        id_: int,
        name: str = None,
        description: str = None,
        image: str = None,
        partitioning: str = None,
        vantage6_version: str = None,
        code_url: str = None,
        documentation_url: str = None,
        functions: List[dict] = None,
        refresh_digest: bool = None,
    ) -> dict:
        """
        Update an algorithm in the algorithm store

        Parameters
        ----------
        id_ : int
            Id of the algorithm
        name : str
            Name of the algorithm
        description : str
            Description of the algorithm
        image : str
            Docker image of the algorithm
        partitioning : str
            Partitioning of the algorithm (horizontal or vertical)
        vantage6_version : str
            Vantage6 version of the algorithm
        code_url : str
            URL to the repository containing the algorithm code
        documentation_url : str, optional
            URL to the documentation of the algorithm
        functions : list[dict]
            List of functions of the algorithm. Each function is a dict with
            the following keys:
            - name: str
                Name of the function
            - description: str, optional
                Description of the function
            - type: string
                Type of the function (central or federated)
            - databases: list[dict]
                List of databases of the function. Each database is a dict with
                the following keys:
                - name: str
                    Name of the database
                - description: str, optional
                    Description of the database
            - arguments: list[dict]
                List of arguments of the function. Each argument is a dict with
                the following keys:
                - name: str
                    Name of the argument
                - description: str, optional
                    Description of the argument
                - type: str
                    Type of the argument. Can be 'string', 'integer', 'float',
                    'boolean', 'json', 'column', 'organization' or 'organizations'
            - ui_visualizations: list[dict]
                List of UI visualizations of the function. Each visualization
                is a dict with the following keys:
                - name: str
                    Name of the visualization
                - description: str, optional
                    Description of the visualization
                - type: str
                    Type of the visualization. Can be 'table'
                - schema: dict, optional
                    Visualization details. For example, for a table, the schema
                    could be a dict with the following keys:
                    - location: list[str]
                        Where data to be visualized are stored in the results. For
                        example, if the data is stored in the 'data' key of the
                        results, the location would be ['data'].
                    - columns: list[str]
                        List of column names to visualize
            refresh_digest : bool, optional
                Whether to refresh the digest of the algorithm. This is useful
                when the algorithm image has been updated before the algorithm was
                in review.

        Returns
        -------
        dict
            The updated algorithm
        """
        body = {}
        if name:
            body["name"] = name
        if description:
            body["description"] = description
        if image:
            body["image"] = image
        if partitioning:
            body["partitioning"] = partitioning
        if vantage6_version:
            body["vantage6_version"] = vantage6_version
        if code_url:
            body["code_url"] = code_url
        if documentation_url:
            body["documentation_url"] = documentation_url
        if functions:
            body["functions"] = functions
        if refresh_digest:
            body["refresh_digest"] = refresh_digest

        return self.parent.request(
            f"algorithm/{id_}",
            method="PATCH",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
            json=body,
        )
