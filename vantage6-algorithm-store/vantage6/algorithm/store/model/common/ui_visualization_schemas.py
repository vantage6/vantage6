"""
This file describes how the JSON schema for different types of UI visualizations
should be structured. The schema is used to validate input data.
"""

from vantage6.algorithm.store.model.common.enums import VisualizationType


# To visualize a table in the UI, the algorithm result should contain a table that
# is structured as follows:
# [
#    { "column1": "value1", "column2": "value2", ... },
#    { "column1": "value3", "column2": "value4", ... },
# ]
table_schema = {
    "type": "object",
    "properties": {
        # indicate where in the results the table can be found. E.g. if the table is
        # in results['data']['table'], the location should be ['data', 'table']. If it
        # is not specified, the table is assumed to be the root of the results.
        "location": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
        # columns of the table. Specify this if you only want to visualize a subset of
        # the columns in the table. Example value: ["column1", "column2"]
        "columns": {
            "type": "array",
            "items": {
                "type": "string",
            },
        },
    },
    "additionalProperties": False,
}


def get_schema_for_visualization(visualization_type: str) -> dict:
    """
    Get the schema for a specific visualization type.

    Parameters
    ----------
    visualization_type : str
        Type of the visualization.

    Returns
    -------
    dict
        JSON validation schema for the visualization type.

    Raises
    ------
    ValueError
        If the visualization type is not supported.
    """
    if visualization_type == VisualizationType.TABLE.value:
        return table_schema
    else:
        raise ValueError(f"Visualization type '{visualization_type}' is not supported.")
