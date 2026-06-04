"""
Test the preprocessing functionality of the vantage6-algorithm-tools package.

To run only this test, from the vantage6 root directory run:
python -m unittest vantage6-algorithm-tools.tests.test_preprocessing
"""

import unittest
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from vantage6.algorithm.client.mock_client import MockAlgorithmClient
from vantage6.algorithm.preprocessing.filtering import select_rows


def random_date(
    start: datetime, end: datetime, fmt: str = "%Y-%m-%d", seed: int = None
) -> str:
    """
    Generate a random date between start and end.

    Arguments:
    - start: datetime object indicating the start date.
    - end: datetime object indicating the end date.
    - fmt: str format in which to return the date.
    - seed: Optional; an integer seed for the random number generator.

    Returns:
    - A string representation of the random date in the specified format.
    """

    # Set the seed only if provided.
    if seed is not None:
        np.random.seed(seed)

    delta = end - start
    random_days = np.random.randint(0, delta.days + 1)
    return (start + timedelta(days=random_days)).strftime(fmt)


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
    education_mapping = {
        "High School": 1,
        "Bachelor": 2,
        "Master": 3,
        "PhD": 4,
    }
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

    # Generate number of rows for each patient
    rows_per_patient = np.random.poisson(avg_rows_per_patient, n_patients)

    # Lists to store the data
    patient_ids = []
    genders = []
    birthdates = []
    education_levels = []
    weights = []

    start_u = pd.Timestamp("2020-01-01").value // 10**9
    end_u = pd.Timestamp("2023-01-01").value // 10**9

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
            weights.extend(np.random.randint(weight - 5, weight + 5, size=count))
        else:
            weights.extend([np.nan] * count)

    # Treatment data
    all_treatments = ["Treatment " + str(i) for i in range(1, 51)]  # 50 treatments
    treatment_names = np.random.choice(all_treatments, sum(rows_per_patient))
    all_diseases = ["Disease A" + str(i).zfill(2) for i in range(10)]  # 10 diseases
    diagnosis_desc = np.random.choice(all_diseases, sum(rows_per_patient))

    start_dates = pd.to_datetime(
        np.random.randint(start_u, end_u, sum(rows_per_patient)), unit="s"
    )

    end_dates = [
        (
            date + pd.Timedelta(days=np.random.randint(1, 60))
            if np.random.random() < 0.8
            else pd.NaT
        )
        for date in start_dates
    ]

    # Generate blood pressures and heart rates based on disease diagnosis
    # integer value
    disease_numbers = [int(disease.split("A")[-1]) for disease in diagnosis_desc]
    blood_pressures = [
        120 + 5 * (number - 5) + np.random.randint(4) for number in disease_numbers
    ]
    heart_rates = [
        70 + 5 * (number - 5) + np.random.randint(4) for number in disease_numbers
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
        np.random.randint(10, 500) if med is not None else None for med in med_choice
    ]

    # Convert birthdates to string if specified
    if date_as_str:
        birthdates = [birthdate.strftime("%Y-%m-%d") for birthdate in birthdates]

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
    def test_preprocessing_batch_1(self):
        """
        Tests the following preprocessing functions:
        - select_rows
        - select_columns
        - drop_columns
        """

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
                            "function": "drop_columns",
                            "parameters": {"columns": ["education"]},
                        },
                    ],
                }
                for dataset in datasets
            ]
        ]
        mockclient = MockAlgorithmClient(datasets=datasets, module="mock_package")

        org_ids = [org["id"] for org in mockclient.organization.list()]

        child_task = mockclient.task.create(
            method="execute",
            organizations=org_ids,
        )

        result = pd.read_json(mockclient.result.get(id_=child_task.get("id")))

        self.assertTrue(result["age"].min() > 50)
        self.assertTrue(result.shape[1] == 4)

    def test_preprocessing_batch_2(self):
        """
        Tests the following preprocessing functions:
        - calculate_age
        - filter_by_date
        - group_statistics
        - timedelta
        - extract_from_string
        - collapse
        - impute
        - encode
        - drop_columns
        """

        datasets = [generate_treatment_example_df(10, 3, 42, date_as_str=True)]
        datasets = [
            [
                {
                    "database": dataset,
                    "type_": "csv",
                    "preprocessing": [
                        {  # birth date to age
                            "function": "calculate_age",
                            "parameters": {
                                "column": "birthdate",
                                "keep_original": False,
                            },
                        },
                        {  # filter by start date after 2020-06-01
                            "function": "filter_by_date",
                            "parameters": {
                                "column": "start_date",
                                "start_date": "2020-06-01",
                            },
                        },
                        {  # add min bloodpressure
                            "function": "group_statistics",
                            "parameters": {
                                "group_columns": "patient_id",
                                "target_columns": "blood_pressure",
                                "aggregation": "min",
                                "prefix": "",
                            },
                        },
                        {  # add max bloodpressure
                            "function": "group_statistics",
                            "parameters": {
                                "group_columns": "patient_id",
                                "target_columns": "blood_pressure",
                                "aggregation": "max",
                                "prefix": "",
                            },
                        },
                        {  # add number of diseases and meds
                            "function": "group_statistics",
                            "parameters": {
                                "group_columns": "patient_id",
                                "target_columns": [
                                    "diagnosis_desc",
                                    "medication",
                                ],
                                "aggregation": "count",
                                "prefix": "",
                            },
                        },
                        {  # add treatment duration
                            "function": "timedelta",
                            "parameters": {
                                "column": "start_date",
                                "to_date_column": "end_date",
                                "output_column": "treatment_duration",
                            },
                        },
                        {  # extract treatment code
                            "function": "extract_from_string",
                            "parameters": {
                                "column": "treatment_name",
                                "pattern": r"(\d+)",
                                "output_column": "treatment_code",
                                "keep_original": False,
                            },
                        },
                        {  # collapse to patient
                            "function": "collapse",
                            "parameters": {
                                "group_columns": "patient_id",
                                "aggregation": {
                                    "medication": list,
                                    "diagnosis_desc": list,
                                    "dosage": "mean",
                                    "blood_pressure": "mean",
                                    "heart_rate": "mean",
                                    "weight": "mean",
                                },
                                "default_aggregation": "last",
                            },
                        },
                        {  # impute weight by median patient weight
                            "function": "impute",
                            "parameters": {
                                "strategy": "median",
                                "columns": "weight",
                            },
                        },
                        {  # impute weight by median patient weight
                            "function": "impute",
                            "parameters": {
                                "strategy": "median",
                                "columns": "weight",
                            },
                        },
                        {  # recode education_level
                            "function": "encode",
                            "parameters": {
                                "columns": ["education_level"],
                                "mapping": {
                                    "Masters": 4,
                                    "Associate Degree": 2,
                                    "Doctorate": 5,
                                    "Bachelor Degree": 3,
                                    "High School": 1,
                                },
                            },
                        },
                        {  # recode gender
                            "function": "encode",
                            "parameters": {
                                "columns": ["gender"],
                                "mapping": {"Female": 2, "Male": 1},
                            },
                        },
                        {  # drop some columns
                            "function": "drop_columns",
                            "parameters": {
                                "columns": [
                                    "patient_id",
                                    "diagnosis_desc",
                                    "start_date",
                                    "end_date",
                                    "medication",
                                ]
                            },
                        },
                    ],
                }
                for dataset in datasets
            ]
        ]

        mockclient = MockAlgorithmClient(datasets=datasets, module="mock_package")
        org_ids = [org["id"] for org in mockclient.organization.list()]
        child_task = mockclient.task.create(
            method="execute",
            organizations=org_ids,
        )
        result = pd.read_json(mockclient.result.get(id_=child_task.get("id")))

        self.assertTrue(result.shape == (9, 13))
        self.assertTrue(
            np.array_equal(
                result.columns,
                [
                    "gender",
                    "education_level",
                    "dosage",
                    "blood_pressure",
                    "heart_rate",
                    "weight",
                    "age",
                    "blood_pressure_min",
                    "blood_pressure_max",
                    "diagnosis_desc_count",
                    "medication_count",
                    "treatment_duration",
                    "treatment_code",
                ],
            )
        )

    def test_preprocessing_batch_3(self):
        """
        Tests the following preprocessing functions:
        - discretize_column
        - rename_columns
        - change_column_type
        - one_hot_encode
        - min_max_scale
        """
        df = get_test_dataframe()
        datasets = [df.iloc[:5]]
        datasets = [
            [
                {
                    "database": dataset,
                    "type_": "csv",
                    "preprocessing": [
                        {
                            "function": "discretize_column",
                            "parameters": {
                                "column_name": "age",
                                "bins": [0, 35, 45, 55, 120],
                            },
                        },
                        {
                            "function": "change_column_type",
                            "parameters": {
                                "columns": ["age"],
                                "target_type": "str",
                            },
                        },
                        {
                            "function": "one_hot_encode",
                            "parameters": {
                                "column": "color_preference",
                                "categories": ["Blue", "Red", "Green"],
                                "prefix": "col",
                            },
                        },
                        {
                            "function": "min_max_scale",
                            "parameters": {
                                "min_vals": [0],
                                "max_vals": [100000],
                                "columns": ["income"],
                            },
                        },
                        {
                            "function": "rename_columns",
                            "parameters": {"new_names": {"income": "inc_norm"}},
                        },
                        {
                            "function": "select_rows",
                            "parameters": {"query": "inc_norm<0.9"},
                        },
                    ],
                }
                for dataset in datasets
            ]
        ]
        mockclient = MockAlgorithmClient(datasets=datasets, module="mock_package")
        org_ids = [org["id"] for org in mockclient.organization.list()]
        child_task = mockclient.task.create(
            method="execute",
            organizations=org_ids,
        )
        result = pd.read_json(mockclient.result.get(id_=child_task.get("id")))
        assert result.to_json() == (
            '{"age":{"1":"(55, 120]","2":"(0, 35]","4":"(0, 35]"},"inc_nor'
            'm":{"1":0.62677,"2":0.12963,"4":0.5687},"education":{"1":"Mas'
            'ter","2":"Bachelor","4":"Bachelor"},"purchased_product":{"1":'
            '1,"2":0,"4":1},"col_Blue":{"1":0,"2":0,"4":0},"col_Green":{"1'
            '":0,"2":1,"4":0},"col_Red":{"1":1,"2":0,"4":1},"col_unknown":'
            '{"1":0,"2":0,"4":0}}'
        )

    def test_preprocessing_batch_4(self):
        """
        Tests the following preprocessing functions:
        - assign_column
        - standard_scale
        - filter_range
        - to_timedelta
        - to_datetime
        """
        df = get_test_dataframe()

        # Set start and end dates for random date generation
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2022, 12, 31)

        # Generate a new column with random dates in string format
        magic_fmt = "(%d)+(%m)=(%Y)"
        # df["magic_date"] = [
        #     random_date(start_date, end_date, fmt=magic_fmt)
        #     for _ in range(len(df))
        # ]
        df["magic_date"] = [
            random_date(start_date, end_date, fmt=magic_fmt, seed=i)
            for i in range(len(df))
        ]

        datasets = [df]

        datasets = [
            [
                {
                    "database": dataset,
                    "type_": "csv",
                    "preprocessing": [
                        {
                            "function": "assign_column",
                            "parameters": {
                                "column_name": "income/age",
                                "expression": "income/age",
                            },
                        },
                        {
                            "function": "assign_column",
                            "parameters": {
                                "column_name": "age_days",
                                "expression": "age * 365",
                            },
                        },
                        {
                            "function": "standard_scale",
                            "parameters": {
                                "means": [1904.2572161956832],
                                "stds": [813.9212391187492],
                                "columns": ["income/age"],
                            },
                        },
                        {
                            "function": "filter_range",
                            "parameters": {
                                "column": "income/age",
                                "min_value": 0,
                            },
                        },
                        {
                            "function": "to_timedelta",
                            "parameters": {
                                "input_column": "age_days",
                                "output_column": "age_days_td",
                            },
                        },
                        {
                            "function": "change_column_type",
                            "parameters": {
                                "columns": ["age_days_td"],
                                "target_type": "str",
                            },
                        },
                        {
                            "function": "to_datetime",
                            "parameters": {
                                "column": "magic_date",
                                "fmt": magic_fmt,
                            },
                        },
                        {
                            "function": "change_column_type",
                            "parameters": {
                                "columns": ["magic_date"],
                                "target_type": "str",
                            },
                        },
                        {
                            "function": "select_rows",
                            "parameters": {"query": "age==23 & education=='Master'"},
                        },
                    ],
                }
                for dataset in datasets
            ]
        ]
        mockclient = MockAlgorithmClient(datasets=datasets, module="mock_package")
        org_ids = [org["id"] for org in mockclient.organization.list()]
        child_task = mockclient.task.create(
            method="execute",
            organizations=org_ids,
        )
        result = pd.read_json(mockclient.result.get(id_=child_task.get("id")))

        expected = (
            '{"age":{"171":23,"342":23},"income":{"171":62026,"342":44074},'
            '"education":{"171":"Master","342":"Master"},"color_preference":'
            '{"171":"Green","342":"Green"},"purchased_product":{"171":1,"342":'
            '0},"magic_date":{"171":"2022-11-12","342":"2020-01-20"},"income\/'
            'age":{"171":0.9737126326,"342":0.0147479299},"age_days":{"171":'
            '8395,"342":8395},"age_days_td":{"171":"8395 days","342":"8395 '
            'days"}}'
        )
        json_result = result.to_json()
        assert json_result == expected, f"{json_result} != {expected}"


class TestSelectRows(unittest.TestCase):
    def test_query(self):
        df = pd.DataFrame(
            {"A": range(1, 6), "B": range(10, 0, -2), "C C": range(10, 5, -1)}
        )

        query = "A > B"
        self.assertTrue(select_rows(df, query).shape == (1, 3))
