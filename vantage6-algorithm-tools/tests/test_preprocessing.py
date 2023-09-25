"""Test the preprocessing functionality of the vantage6-algorithm-tools package.

To run only this test, from the vantage6 root directory run:


"""
import unittest

import numpy as np
import pandas as pd

from vantage6.algorithm.tools.mock_client import MockAlgorithmClient
from vantage6.algorithm.tools.preprocessing.functions import select_rows


def get_test_dataframe(n=1000, seed=0):
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


def generate_treatment_example_df(
    n_patients, avg_rows_per_patient, random_state, date_as_str=True
):
    np.random.seed(random_state)

    # Data generation functions
    def random_dates(start, end, n=10):
        start_u = start.value // 10**9
        end_u = end.value // 10**9
        return pd.to_datetime(np.random.randint(start_u, end_u, n), unit="s")

    # Generate number of rows for each patient
    rows_per_patient = np.random.poisson(avg_rows_per_patient, n_patients)

    # Lists to store the data
    patient_ids = []
    genders = []
    birthdates = []
    education_levels = []
    weights = []

    for i, count in enumerate(rows_per_patient, 1):
        # Patient attributes
        gender = np.random.choice(["Male", "Female"])
        age = np.random.randint(18, 80)
        education = np.random.choice(
            [
                "High School",
                "Associate Degree",
                "Bachelor Degree",
                "Masters",
                "Doctorate",
            ]
        )

        birth_year = 2021 - age  # Assuming treatment date in 2021 on average
        birth_date = pd.Timestamp(
            year=birth_year,
            month=np.random.randint(1, 13),
            day=np.random.randint(1, 29),
        )

        patient_ids.extend([i] * count)
        genders.extend([gender] * count)
        birthdates.extend([birth_date] * count)
        education_levels.extend([education] * count)
        if np.random.choice([True, False], p=[0.75, 0.25]):
            weight = np.random.uniform(50, 100)
            weights.extend(
                np.random.randint(weight - 5, weight + 5, size=count)
            )
        else:
            weights.extend([np.nan] * count)

    # Treatment data
    all_treatments = [
        "Treatment " + str(i) for i in range(1, 51)
    ]  # 50 treatments
    treatment_names = np.random.choice(all_treatments, sum(rows_per_patient))
    all_diseases = [
        "Disease A" + str(i).zfill(2) for i in range(10)
    ]  # 10 diseases
    diagnosis_desc = np.random.choice(all_diseases, sum(rows_per_patient))
    start_dates = random_dates(
        pd.Timestamp("2020-01-01"),
        pd.Timestamp("2023-01-01"),
        sum(rows_per_patient),
    )
    end_dates = [
        date + pd.Timedelta(days=np.random.randint(1, 60))
        if np.random.random() < 0.8
        else pd.NaT
        for date in start_dates
    ]

    # Generate blood pressures and heart rates based on disease diagnosis
    # integer value
    disease_numbers = [
        int(disease.split("A")[-1]) for disease in diagnosis_desc
    ]
    blood_pressures = [
        120 + 5 * (number - 5) + np.random.randint(4)
        for number in disease_numbers
    ]
    heart_rates = [
        70 + 5 * (number - 5) + np.random.randint(4)
        for number in disease_numbers
    ]

    # Convert dates to string if specified
    if date_as_str:
        start_dates = [
            date.strftime("%Y-%m-%d") if not pd.isnull(date) else ""
            for date in start_dates
        ]
        end_dates = [
            date.strftime("%Y-%m-%d") if not pd.isnull(date) else ""
            for date in end_dates
        ]

    # Medication and dosage data
    medications = ["MedA", "MedB", "MedC", "MedD", "MedE"]
    med_choice = np.random.choice(medications + [None], sum(rows_per_patient))
    dosages = [
        np.random.randint(10, 500) if med is not None else None
        for med in med_choice
    ]

    # Convert birthdates to string if specified
    if date_as_str:
        birthdates = [
            birthdate.strftime("%Y-%m-%d") for birthdate in birthdates
        ]

    # Create DataFrame
    df = pd.DataFrame(
        {
            "patient_id": patient_ids,
            "gender": genders,
            "birthdate": birthdates,
            "education_level": education_levels,
            "treatment_name": treatment_names,
            "diagnosis_desc": diagnosis_desc,
            "start_date": start_dates,
            "end_date": end_dates,
            "medication": med_choice,
            "dosage": dosages,
            "blood_pressure": blood_pressures,
            "heart_rate": heart_rates,
            "weight": weights,
        }
    )
    return df


class TestPreprocessing(unittest.TestCase):
    def test_preprocessing(self):
        df = get_test_dataframe()

        datasets = [df]
        datasets = [
            [
                {
                    "database": dataset,
                    "type_": "csv",
                    "preprocessing": [
                        {
                            "function": "select_rows",
                            "parameters": {"query": "age>50"},
                        },
                        {
                            "function": "select_columns",
                            "parameters": {
                                "columns": [
                                    "age",
                                    "income",
                                    "education",
                                    "color_preference",
                                    "purchased_product",
                                ]
                            },
                        },
                        {
                            "function": "select_columns_by_index",
                            "parameters": {"columns": [0, 1, 2, 3]},
                        },
                        {
                            "function": "drop_columns",
                            "parameters": {"columns": ["education"]},
                        },
                        {
                            "function": "drop_columns_by_index",
                            "parameters": {"columns": [-1]},
                        },
                    ],
                }
                for dataset in datasets
            ]
        ]
        mockclient = MockAlgorithmClient(
            datasets=datasets, module="mock_package"
        )

        org_ids = [org["id"] for org in mockclient.organization.list()]

        input_ = {"method": "execute", "kwargs": {}}
        child_task = mockclient.task.create(
            organizations=org_ids,
            input_=input_,
        )

        result = pd.read_json(mockclient.result.get(id_=child_task.get("id")))

        self.assertTrue(result["age"].min() > 50)
        self.assertTrue(result.shape[1] == 2)


class TestSelectRows(unittest.TestCase):
    def test_query(self):
        df = pd.DataFrame(
            {"A": range(1, 6), "B": range(10, 0, -2), "C C": range(10, 5, -1)}
        )

        query = "A > B"
        self.assertTrue(select_rows(df, query).shape == (1, 3))
