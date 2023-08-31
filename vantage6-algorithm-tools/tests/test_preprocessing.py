"""Test the preprocessing functionality of the vantage6-algorithm-tools package.

python -m unittest vantage6-algorithm-tools.tests.test_preprocessing

"""

import unittest

import numpy as np
import pandas as pd

from vantage6.algorithm.tools.mock_client import MockAlgorithmClient


def test_dataframe(n=1000, seed=0):
    # Set a seed for reproducibility
    np.random.seed(seed)

    # Generate synthetic age and income (numerical features)
    age = np.random.randint(20, 70, n)
    income = np.random.randint(10000, 100000, n)

    # Generate synthetic education (ordinal feature)
    education_categories = ["High School", "Bachelor", "Master", "PhD"]
    education_levels = np.random.choice(
        education_categories, n, p=[0.5, 0.3, 0.15, 0.05]
    )

    # Map education levels to ordinal numbers
    education_mapping = {"High School": 1, "Bachelor": 2, "Master": 3, "PhD": 4}
    education = np.vectorize(education_mapping.get)(education_levels)

    # Generate synthetic color_preference (nominal feature)
    color_categories = ["Red", "Blue", "Green", "Yellow"]
    color_preference = np.random.choice(color_categories, n)

    # Calculate synthetic target variable (binary feature)
    # Here we say that the chance of having purchased the product depends on
    # the age, income, education, and color_preference
    prob_purchase = (
        0.1 * age / 70
        + 0.2 * income / 100000
        + 0.3 * education / 4
        + 0.4 * (color_preference == "Red")
    )
    purchased_product = np.random.binomial(1, prob_purchase)

    # Create a DataFrame
    df = pd.DataFrame(
        {
            "age": age,
            "income": income,
            "education": education_levels,
            "color_preference": color_preference,
            "purchased_product": purchased_product,
        }
    )

    return df


class TestPreprocessing(unittest.TestCase):
    def test_preprocessing(self):
        df = test_dataframe()

        datasets = [df]
        datasets = [
            [
                {
                    "database": dataset,
                    "type_": "csv",
                    "preprocessing": {"select_rows": "age>50"},
                }
                for dataset in datasets
            ]
        ]
        mockclient = MockAlgorithmClient(datasets=datasets, module="mock_package")

        org_ids = [org["id"] for org in mockclient.organization.list()]
        org_ids

        input_ = {"method": "execute", "master": True, "kwargs": {}}
        child_task = mockclient.task.create(
            organizations=org_ids,
            input_=input_,
        )

        try:
            result = pd.read_json(mockclient.result.get(id_=child_task.get("id")))
        except:
            result = pd.read_json(mockclient.result.get(id_=child_task.get("id") + 1))

        self.assert_(result["age"].min() > 50)
