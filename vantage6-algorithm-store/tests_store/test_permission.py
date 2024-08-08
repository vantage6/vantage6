import unittest

# from flask_principal import Principal, Identity, identity_loaded

# from vantage6.algorithm.store.model.rule import Operation
# from vantage6.algorithm.store.permission import RuleCollection
# from vantage6.common.globals import InstanceType
# from vantage6.backend.common import test_context
# from vantage6.algorithm.store.model.base import Database, DatabaseSessionManager
# from vantage6.algorithm.store import AlgorithmStoreApp
# from vantage6.algorithm.store.globals import PACKAGE_FOLDER
# from vantage6.algorithm.store.model.policy import Policy
# from vantage6.algorithm.store.model.role import Role
# from vantage6.algorithm.store.model.rule import Rule
# from vantage6.algorithm.store.model.user import User
# from vantage6.algorithm.store.model.vantage6_server import Vantage6Server
from .base.unittest_base import TestResources


# TODO create unit tests for this module - this was now abandoned due to expected
# refactoring work that will put a similar class in vantage6.backend.common
class TestPermission(TestResources):
    """Test the vantage6.algorithm.store.permission module"""

    pass

    # @classmethod
    # def setUp(cls):
    #     """Called immediately before running a test method."""
    #     super().setUp()
    #     Principal(cls.server.app, use_sessions=False)
    #     cls.ctx = cls.server.app.app_context()
    #     cls.ctx.push()

    #     # Load an identity
    #     @identity_loaded.connect_via(cls.server.app)
    #     def on_identity_loaded(sender, identity):
    #         identity.provides.add(Operation.VIEW)

    #     # Set up an identity for the test
    #     identity = Identity("test_user")
    #     identity_loaded.send(cls.server.app, identity=identity)

    #     # @cls.server.app.before_request
    #     # def before_request():
    #     #     # Assuming you have a way to determine user roles, adjust as necessary
    #     #     identity = Identity("user_id")
    #     #     identity.provides.add("role_or_permission")
    #     #     identity_loaded.send(cls.server.app, identity=identity)

    #     # # Manually load an identity for testing
    #     # identity = Identity("test_user")
    #     # identity_loaded.send(cls.server.app, identity=identity)

    # @classmethod
    # def tearDown(cls):
    #     """Called immediately after running a test method."""
    #     super().tearDown()
    #     cls.ctx.pop()

    # def test_rule_collection(self):
    #     """Test RuleCollection class"""

    #     # Create a RuleCollection object
    #     self.server.permissions.collections["test"] = RuleCollection("test")
    #     rule_collection = self.server.permissions.collections["test"]

    #     # Add a rule to the RuleCollection object
    #     rule_collection.add(Operation.VIEW)

    #     # Check if the RuleCollection object has the permission for a certain operation
    #     self.assertTrue(rule_collection.has_permission(Operation.VIEW))
    #     self.assertFalse(rule_collection.has_permission(Operation.CREATE))


if __name__ == "__main__":
    unittest.main()
