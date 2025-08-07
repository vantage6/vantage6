import pandas as pd
from typing import Any

from vantage6.algorithm.tools.util import info
from vantage6.algorithm.tools.decorators import algorithm_client
from vantage6.algorithm.tools.decorators import data
from vantage6.algorithm.client import AlgorithmClient

@data(1)
@algorithm_client
def central(
    client: AlgorithmClient, df1: pd.DataFrame, arg1
) -> Any:

    organizations = client.organization.list()
    org_ids = [organization.get("id") for organization in organizations]

    info("Defining input parameters")
    large_padding = "X" * 100_000  # 100MB of 'X'

    input_ = {
        "method": "partial",
        "kwargs": {
            "padding": large_padding  # artificial payload
        }
    }

    task = client.task.create(
        input_=input_,
        organizations=org_ids,
        name="Example subtask",
        description="This is an example subtask"
    )

    task_id = task['id']
    results = client.retrieve_results(task_id)

    sum_female_age = 0
    sum_male_age = 0
    for item in results:
        sum_female_age += item["age"]["female"]
        sum_male_age += item["age"]["male"]

    output = {
        "sum_female_age": sum_female_age,
        "sum_male_age": sum_male_age
    }

    return output
