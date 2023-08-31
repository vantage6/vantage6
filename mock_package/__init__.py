def execute(
    mock_client,
    mock_data,
    **kwargs,
):
    """
    This will be called by the mock client task
    """
    return mock_data[0].to_json()
