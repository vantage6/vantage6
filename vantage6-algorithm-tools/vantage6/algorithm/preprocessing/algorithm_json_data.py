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
            "default_aggregation": {
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
    },
    "group_statistics": {
        "arguments": {
            "group_columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
            "target_columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
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
        },
    },
    "rename_columns": {
        "arguments": {
            "old_names": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
            "new_names": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
        },
    },
    "redefine_column": {
        "arguments": {
            "column_name": {
                "type": AlgorithmArgumentType.COLUMN.value,
            },
        },
    },
    "change_column_type": {
        "arguments": {
            "columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
            "target_type": {
                "allowed_values": [
                    "int",
                    "float",
                    "str",
                    "bool",
                    "category",
                    "datetime",
                    "timedelta",
                    "object",
                ],
            },
        },
    },
    "to_datetime": {
        "arguments": {
            "columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
            "errors": {
                "allowed_values": ["raise", "ignore", "coerce"],
            },
        },
    },
    "to_timedelta": {
        "arguments": {
            "input_column": {
                "type": AlgorithmArgumentType.COLUMN.value,
            },
            "unit": {
                "allowed_values": [
                    "W",
                    "days",
                    "hours",
                    "m",
                    "s",
                    "ms",
                    "us",
                    "ns",
                ],
            },
            "output_column": {
                "conditional_on": "duration",
                "conditional_value": None,
                "conditional_operator": "!=",
            },
            "errors": {
                "allowed_values": ["raise", "ignore", "coerce"],
            },
        },
    },
    "timedelta": {
        "arguments": {
            "column": {
                "type": AlgorithmArgumentType.COLUMN.value,
            },
            "to_date_column": {
                "type": AlgorithmArgumentType.COLUMN.value,
            },
            "to_date": {
                "conditional_on": "to_date_column",
                "conditional_value": None,
                "conditional_operator": "!=",
            },
        },
    },
    "calculate_age": {
        "arguments": {
            "column": {
                "type": AlgorithmArgumentType.COLUMN.value,
            },
        },
    },
    "min_max_scale": {
        "arguments": {
            "columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
        },
    },
    "standard_scale": {
        "arguments": {
            "columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
        },
    },
    "one_hot_encode": {
        "arguments": {
            "column": {
                "type": AlgorithmArgumentType.COLUMN.value,
            },
        },
    },
    "encode": {
        "arguments": {
            "columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
            "unknown_value_type": {
                "allowed_values": ["str", "int"],
            },
        },
    },
    "discretize_column": {
        "arguments": {
            "column_name": {
                "type": AlgorithmArgumentType.COLUMN.value,
            },
        },
    },
    "extract_from_string": {
        "arguments": {
            "column": {
                "type": AlgorithmArgumentType.COLUMN.value,
            },
        },
    },
    "impute": {
        "arguments": {
            "columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
            "missing_values_type": {
                "allowed_values": ["str", "int", "float"],
            },
            "strategy": {
                "allowed_values": ["mean", "median", "most_frequent", "constant"],
            },
            "group_columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
            "fill_value": {
                "conditional_on": "strategy",
                "conditional_value": "constant",
                "conditional_operator": "==",
            },
            "fill_value_type": {
                "conditional_on": "strategy",
                "conditional_value": "constant",
                "conditional_operator": "==",
                "allowed_values": ["str", "int", "float"],
            },
        },
    },
    "filter_range": {
        "arguments": {
            "column": {
                "type": AlgorithmArgumentType.COLUMN.value,
            },
        },
    },
    "select_columns": {
        "arguments": {
            "columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
        },
    },
    "drop_columns": {
        "arguments": {
            "columns": {
                "type": AlgorithmArgumentType.COLUMNS.value,
            },
        },
    },
    "filter_by_date": {
        "arguments": {
            "column": {
                "type": AlgorithmArgumentType.COLUMN.value,
            },
        },
    },
}
