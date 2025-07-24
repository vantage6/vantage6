import pandas as pd
from typing import Any

from vantage6.algorithm.tools.util import info, warn, error
from vantage6.algorithm.tools.decorators import algorithm_client
from vantage6.algorithm.tools.decorators import data
from vantage6.algorithm.client import AlgorithmClient


@data(1)
@algorithm_client
def partial(
    client: AlgorithmClient, df1: pd.DataFrame, padding: str = ""
) -> Any:
    result = df1[["gender", "age"]].groupby("gender").mean()
    result_dict = result.to_dict()
    result_dict["padding"] = padding
    return result_dict