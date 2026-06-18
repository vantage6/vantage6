average = {
    "collaboration": 1,
    "organizations": [1],
    "name": "test_average_task",
    "image": "ghcr.io/vantage6/algorithm/demo/average:latest",
    "description": "",
    "method": "central_average",
    "arguments": {
        "column_name": "Age",
    },
    "databases": [{"label": "olympic-athletes"}],
}

kaplan_meier = {
    "collaboration": 1,
    "organizations": [1],
    "name": "test_average_task",
    "image": "ghcr.io/vantage6/algorithm/kaplan-meier:latest",
    "description": "",
    "method": "kaplan_meier_central",
    "arguments": {
        "time_column_name": "days",
        "censor_column_name": "censor",
        "organizations_to_include": [1, 2, 3],
    },
    "databases": [{"label": "kaplan-meier-test"}],
}

args = {"average": average, "kaplan_meier": kaplan_meier}
