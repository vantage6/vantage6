"""
This module provides a JSON dict with data for each of the preprocessing functions that
cannot be derived from the function signature.
"""

# TODO type (for column / organization / ...)
# TODO conditional operators
from vantage6.common.enum import AlgorithmArgumentType


PREPROCESSING_FUNCTIONS_JSON_DATA = {
    "collapse": {
        "arguments": {
            "group_columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
            # TODO add additional frontend argument for checkbox between aggregation
            # strategy and aggregation dict
            "aggregation_strategy": {
                "allowed_values": [
                    "sum",
                    "mean",
                    "min",
                    "max",
                    "count",
                    "len",
                    "std",
                    "var",
                    "first",
                    "last",
                    "nunique",
                    "size",
                    "list",
                    "set",
                    "any",
                    "all",
                ],
                "conditional_on": "single_aggregation_strategy",
                "conditional_value": True,
                "conditional_operator": "==",
            },
            "aggregation_dict": {
                "conditional_on": "single_aggregation_strategy",
                "conditional_value": False,
                "conditional_operator": "==",
            },
        },
        "frontend_arguments": {
            "single_aggregation_strategy": {
                "before_argument": "aggregation_strategy",
                "name": "single_aggregation_strategy",
                "display_name": "Single aggregation strategy",
                "description": (
                    "Aggregate all columns using the same strategy if enabled. "
                    "Otherwise, provide a dictionary with strategy per column."
                ),
                "type": AlgorithmArgumentType.BOOLEAN.value,
                "has_default_value": True,
                "default": True,
                "is_frontend_only": True,
            },
        },
    }
}
