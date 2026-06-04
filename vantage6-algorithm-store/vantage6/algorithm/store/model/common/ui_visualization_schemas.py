"""
This file describes how the JSON schema for different types of UI visualizations
should be structured. The schema is used to validate input data.
"""

from vantage6.algorithm.store.model.common.enums import VisualizationType

STRING_ARRAY_DECLARATION = {
    "type": "array",
    "items": {
        "type": "string",
    },
}

DEFAULT_PROPERTIES = {
    # indicate where in the results the data to visualize can be found. E.g. if there is
    # a table to visualize in results['data']['table'], the location should be
    # ['data', 'table']. If it is not specified, the table is assumed to be the root
    # of the results.
    "location": STRING_ARRAY_DECLARATION,
}
# To visualize a table in the UI, the algorithm result should contain a table that
# is structured as follows:
# [
#    { "column1": "value1", "column2": "value2", ... },
#    { "column1": "value3", "column2": "value4", ... },
# ]
TABLE_SCHEMA = {
    "type": "object",
    "properties": DEFAULT_PROPERTIES
    | {
        # columns of the table. Specify this if you only want to visualize a subset of
        # the columns in the table. Example value: ["column1", "column2"]
        "columns": STRING_ARRAY_DECLARATION,
    },
    # TOOD is this used? If not, remove it.
    "additionalProperties": False,
}

LINE_SCHEMA = {
    "type": "object",
    "properties": DEFAULT_PROPERTIES
    | {
        # x-axis column in the table
        "x": {"type": "string"},
        # y-axis column in the table
        "y": {"type": "string"},
        # y axis minimum value
        "y_axis_min": {"type": "number"},
        # y axis maximum value
        "y_axis_max": {"type": "number"},
    },
    "required": ["x", "y"],
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
    if visualization_type == VisualizationType.TABLE:
        return TABLE_SCHEMA
    elif visualization_type == VisualizationType.LINE:
        return LINE_SCHEMA
    else:
        raise ValueError(f"Visualization type '{visualization_type}' is not supported.")
