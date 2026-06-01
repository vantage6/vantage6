import unittest

from vantage6.cli.algorithm.generate_algorithm_json import (
    Function,
    MergePreference,
)


def _noop():
    """Placeholder algorithm function for merge tests."""


class TestGenerateAlgorithmJson(unittest.TestCase):
    def setUp(self):
        MergePreference.reset()

    def test_merge_expands_frontend_arguments(self):
        function = Function(_noop)
        function.json = {
            "name": "collapse",
            "display_name": "Collapse",
            "arguments": [
                {"name": "aggregation_strategy", "type": "string"},
            ],
        }
        function.merge_with_existing_json(
            {
                "frontend_arguments": {
                    "single_aggregation_strategy": {
                        "before_argument": "aggregation_strategy",
                        "name": "single_aggregation_strategy",
                        "display_name": "Single aggregation strategy",
                        "type": "boolean",
                        "has_default_value": True,
                        "default_value": True,
                        "is_frontend_only": True,
                    }
                }
            }
        )
        self.assertNotIn("frontend_arguments", function.json)
        names = [arg["name"] for arg in function.json["arguments"]]
        self.assertEqual(
            names,
            ["single_aggregation_strategy", "aggregation_strategy"],
        )

    def test_merge_adds_missing_key_without_keyerror(self):
        function = Function(_noop)
        function.json = {"name": "assign_column", "display_name": "Assign column"}
        function.merge_with_existing_json(
            {"display_name": "Assign column", "description": "From existing json"}
        )
        self.assertEqual(function.json["description"], "From existing json")


if __name__ == "__main__":
    unittest.main()
