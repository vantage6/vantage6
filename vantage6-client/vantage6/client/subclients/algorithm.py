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
    ) -> list[dict]:
        """
        List algorithms

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

        Returns
        -------
        list[dict]
            List of algorithms
        """
        return self.parent.request(
            "algorithm",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
            params={
                "name": name,
                "description": description,
                "image": image,
                "partitioning": partitioning,
                "v6_version": v6_version,
            },
        )

    @post_filtering(iterable=False)
    def create(
        self,
        name: str,
        description: str,
        image: str,
        partitioning: str,
        vantage6_version: str,
        functions: List[dict],
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


        Returns
        -------
        dict
            The created algorithm
        """
        return self.parent.request(
            "algorithm",
            method="post",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
            json={
                "name": name,
                "image": image,
                "partitioning": partitioning,
                "vantage6_version": vantage6_version,
                "functions": functions,
                "description": description,
            },
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

    def update(
        self,
        id_: int,
        name: str = None,
        description: str = None,
        image: str = None,
        partitioning: str = None,
        vantage6_version: str = None,
        functions: List[dict] = None,
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
        if functions:
            body["functions"] = functions

        return self.parent.request(
            f"algorithm/{id_}",
            method="PATCH",
            is_for_algorithm_store=True,
            headers=self.parent.util._get_server_url_header(),
            json=body,
        )
