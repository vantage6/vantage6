import unittest

from vantage6.common.enum import AlgorithmArgumentType

from vantage6.algorithm.store.resource.schema.input_schema import (
    ArgumentInputSchema,
    FunctionInputSchema,
    coerce_to_store_string,
)


class TestCoerceToStoreString(unittest.TestCase):
    def test_coerce_values(self):
        self.assertIsNone(coerce_to_store_string(None))
        self.assertEqual(coerce_to_store_string(True), "true")
        self.assertEqual(coerce_to_store_string(False), "false")
        self.assertEqual(coerce_to_store_string(-1), "-1")
        self.assertEqual(coerce_to_store_string("constant"), "constant")


class TestArgumentInputSchema(unittest.TestCase):
    def test_accepts_json_boolean_default_and_conditional(self):
        loaded = ArgumentInputSchema().load(
            {
                "name": "strict_mode",
                "type": AlgorithmArgumentType.BOOLEAN.value,
                "has_default_value": True,
                "default_value": True,
                "conditional_on": "toggle",
                "conditional_operator": "==",
                "conditional_value": False,
            }
        )
        self.assertEqual(loaded["default_value"], "true")
        self.assertEqual(loaded["conditional_value"], "false")

    def test_function_schema_accepts_boolean_conditionals(self):
        function = FunctionInputSchema().load(
            {
                "name": "collapse",
                "step_type": "preprocessing",
                "arguments": [
                    {
                        "name": "single_aggregation_strategy",
                        "type": AlgorithmArgumentType.BOOLEAN.value,
                    },
                    {
                        "name": "aggregation_strategy",
                        "type": AlgorithmArgumentType.STRING.value,
                        "has_default_value": True,
                        "default_value": None,
                        "conditional_on": "single_aggregation_strategy",
                        "conditional_operator": "==",
                        "conditional_value": True,
                    },
                ],
            }
        )
        aggregation = next(
            a for a in function["arguments"] if a["name"] == "aggregation_strategy"
        )
        self.assertEqual(aggregation["conditional_value"], "true")


if __name__ == "__main__":
    unittest.main()
