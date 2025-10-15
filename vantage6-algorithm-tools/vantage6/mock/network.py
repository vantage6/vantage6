import pandas as pd

from vantage6.common import info

from vantage6.mock.client import MockAlgorithmClient, MockUserClient
from vantage6.mock.node import MockNode
from vantage6.mock.server import MockServer


class MockNetwork:
    def __init__(
        self,
        module_name: str,
        datasets: list[dict[str, dict[str, str | pd.DataFrame]]],
        collaboration_id: int = 1,
    ):
        """
        Create a mock network to test algorithms.

        This MockNetwork contains all components to simulate algorithm execution in a
        vantage6 network.

        In the case that you do not want to execute a data extraction step, you can
        provide a pandas DataFrame instead of a string for the database value.

        Parameters
        ----------
        module_name : str
            The name of the Python module that contains the algorithm.
        datasets : list[dict[str, dict[str, str | pd.DataFrame]]]
            A dictionary that contains the datasets for each organization. The keys
            are the labels of the datasets used instead of the label specified in the
            node configuration. The values are either a string (path to file or SQL
            connection string) or a pandas DataFrame. In case a DataFrame is provided,
            automatically a data extraction step is performed.
        collaboration_id : int | None
            The id of the collaboration.

        Attributes
        ----------
        nodes : list[MockNode]
            The nodes of the mock network.
        server : MockServer
            The server of the mock network.
        user_client : MockUserClient
            The user client of the mock network.
        algorithm_client : MockAlgorithmClient
            The algorithm client of the mock network.

        Methods
        -------
        get_node(id_: int) -> MockNode
            Get the node with the given id.

        Properties
        ----------
        organization_ids -> list[int]
            The ids of the organizations.
        node_ids -> list[int]
            The ids of the nodes.

        Examples
        --------

        An example of how to create a dataframe and then use this dataframe in a task:

        >>> from vantage6.mock.mock_network import MockNetwork
        >>> network = MockNetwork(
        >>>     module_name="my_algorithm",
        >>>     datasets={"dataset_1": {"database": "mock_data.csv", "db_type": "csv"}},
        >>> )
        >>> client = network.user_client
        >>> client.dataframe.create(
        >>>     label="dataset_1", method="my_method", arguments={}
        >>> )
        >>> client.task.create(
        >>>     method="my_method",
        >>>     organizations=[0],
        >>>     arguments={
        >>>         "example_argument": 10
        >>>     },
        >>>     databases=[{"label": "dataset_1"}]
        >>> )
        >>> results = client.result.from_task(task.get("id"))
        >>> print(results)

        Or in case you do not want to test data extraction you can provide a pandas
        DataFrame instead of a string for the database value:

        >>> network = MockNetwork(
        >>>     module_name="my_algorithm",
        >>>     datasets={"dataset_1": pd.DataFrame({"column_1": [1, 2, 3]})},
        >>> )
        >>> client = network.user_client
        >>> client.task.create(
        >>>     method="my_method",
        >>>     organizations=[0],
        >>>     arguments={
        >>>         "example_argument": 10
        >>>     },
        >>>     databases=[{"label": "dataset_1"}]
        >>> )
        >>> results = client.result.from_task(task.get("id"))
        >>> print(results)
        """
        self.collaboration_id = collaboration_id
        self.module_name = module_name
        self.nodes = []

        organization_ids = list(range(len(datasets)))
        node_ids = list(range(len(datasets)))
        for org_id, node_id, dataset in zip(organization_ids, node_ids, datasets):
            self.nodes.append(
                MockNode(node_id, org_id, collaboration_id, dataset, self)
            )

        self.server = MockServer(self)
        self.user_client = MockUserClient(self)
        self.algorithm_client = MockAlgorithmClient(self)

        info(f"Mock network created with {len(self.nodes)} nodes")

    @property
    def organization_ids(self) -> list[int]:
        """
        The ids of the organizations.

        Returns
        -------
        list[int]
            The ids of the organizations.
        """
        return [node.organization_id for node in self.nodes]

    @property
    def node_ids(self) -> list[int]:
        """
        The ids of the nodes.

        Returns
        -------
        list[int]
            The ids of the nodes.
        """
        return [node.id_ for node in self.nodes]

    def get_node(self, id_: int) -> "MockNode":
        """
        Get the node with the given id.

        Parameters
        ----------
        id_ : int
            The id of the node.

        Raises
        ------
        StopIteration
            If the node with the given id is not found.

        Returns
        -------
        MockNode
            The node with the given id.
        """
        return next(node for node in self.nodes if node.id_ == id_)
