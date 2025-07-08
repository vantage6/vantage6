average = {
    "collaboration": 1,
    "organizations": [1],
    "name": "test_average_task",
    "image": "harbor2.vantage6.ai/demo/average",
    "description": "",
    "input_": {
        "method": "central_average",
        "args": [],
        "kwargs": {"column_name": "Age"},
    },
    "databases": [{"label": "olympic_athletes"}],
}

kaplan_meier = {
    "collaboration": 1,
    "organizations": [1],
    "name": "test_average_task",
    "image": "harbor2.vantage6.ai/algorithms/kaplan-meier",
    "description": "",
    "input_": {
        "method": "kaplan_meier_central",
        "args": [],
        "kwargs": {
            "time_column_name": "days",
            "censor_column_name": "censor",
            "organizations_to_include": [1, 2, 3],
        },
    },
    "databases": [{"label": "kaplan_meier_test"}],
}

args = {"average": average, "kaplan_meier": kaplan_meier}
