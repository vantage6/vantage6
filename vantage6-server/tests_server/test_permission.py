import unittest

from vantage6.server.model.rule import Operation, Scope
from vantage6.server.permission import RuleCollection


class TestRuleCollection(unittest.TestCase):
    def test_permission_attribute_names(self):
        """
        Test that permissions are registered under names such as ``v_own``

        The resources read permissions back with literal attribute names like
        ``self.r.v_own``. Python 3.11 changed how enums with a mixed-in str type
        are formatted, which registered them as ``Operation.VIEW_Scope.OWN``
        instead and broke every permission check, see
        https://github.com/vantage6/vantage6/issues/2512
        """
        collection = RuleCollection("task")
        collection.add(Operation.VIEW, Scope.OWN)
        collection.add(Operation.CREATE, Scope.GLOBAL)
        collection.add(Operation.EDIT)

        self.assertTrue(hasattr(collection, "v_own"))
        self.assertTrue(hasattr(collection, "c_glo"))
        self.assertTrue(hasattr(collection, "e"))
        self.assertFalse(hasattr(collection, "Operation.VIEW_Scope.OWN"))
