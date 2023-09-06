from vantage6.algorithm.tools.decorators import algorithm_client, data


@data()
@algorithm_client
def execute(
    mock_client,
    mock_data,
    **kwargs,
):
    """
    This will be called by the mock client task
    """
    return mock_data.to_json()
