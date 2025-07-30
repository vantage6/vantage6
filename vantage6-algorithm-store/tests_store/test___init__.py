import unittest
from unittest.mock import patch

from vantage6.common.enum import AlgorithmViewPolicies, StorePolicies

from vantage6.algorithm.store import db
from vantage6.algorithm.store.default_roles import DefaultRole, get_default_roles
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Rule
from vantage6.algorithm.store.model.user import User

from .base.unittest_base import TestResources


class TestAlgorithmStoreApp(TestResources):
    def test_setup_policies(self):
        # Create some existing mock policies
        policy1 = Policy(key="policy1", value="value1")
        policy2 = Policy(key="policy2", value="value2")
        policy1.save()
        policy2.save()

        # Create a mock configuration
        config = {
            "policies": {
                StorePolicies.ALGORITHM_VIEW.value: AlgorithmViewPolicies.PUBLIC.value,
                "non_existing_policy": "value",
            },
        }

        # Call the setup_policies method
        self.server.setup_policies(config)

        # Check that the Policy objects are created with the correct values, and that
        # the non-existing policy is ignored and existing policies were deleted
        policies = Policy.get()
        self.assertEqual(
            [(p.key, p.value) for p in policies],
            [
                (
                    StorePolicies.ALGORITHM_VIEW.value,
                    AlgorithmViewPolicies.PUBLIC.value,
                ),
            ],
        )

    @patch("vantage6.algorithm.store.AlgorithmStoreApp._add_default_roles")
    @patch("vantage6.algorithm.store.AlgorithmStoreApp._add_keycloak_id_to_super_user")
    def test_server_startup(self, mock_add_keycloak_id, mock_add_default_roles):
        """Test that the server is started correctly"""

        # ensure root role is present - this role will be assigned to the root user
        # that is created on server startup
        root_role = Role(name=DefaultRole.ROOT.value, rules=Rule.get())
        root_role.save()

        self.server.ctx.config["root_user"] = {
            "username": "superuser",
        }

        self.server.start()

        mock_add_default_roles.assert_called_once()
        mock_add_keycloak_id.assert_called_once()

        root_user = User.get_by_username("superuser")
        self.assertIsNotNone(root_user)
        self.assertEqual(len(root_user.roles), 1)
        self.assertEqual(root_user.roles[0].name, DefaultRole.ROOT.value)

    def test_add_default_roles(self):
        """Test that the default roles are added to the database"""

        # pylint: disable=protected-access
        self.server._add_default_roles(get_default_roles(), db)

        roles = Role.get()
        role_names = [role.value for role in DefaultRole]
        self.assertEqual(len(roles), len(role_names))
        for role in roles:
            self.assertIn(role.name, role_names)

        # run function again to ensure that the roles are not duplicated
        self.server._add_default_roles(get_default_roles(), db)
        self.assertEqual(len(Role.get()), len(role_names))

        # verify that function to get the default roles includes all default roles
        default_role_list_dict = get_default_roles()
        self.assertEqual(len(default_role_list_dict), len(role_names))

        # test that when removing rules from a role, they are re-added when
        # _add_default_roles is run again
        role = Role.get_by_name(DefaultRole.VIEWER.value)
        role.rules = []
        role.save()
        self.server._add_default_roles(get_default_roles(), db)
        role = Role.get_by_name(DefaultRole.VIEWER.value)
        self.assertNotEqual(len(role.rules), 0)
        for r in default_role_list_dict:
            if r["name"] == DefaultRole.VIEWER.value:
                self.assertEqual(len(role.rules), len(r["rules"]))


if __name__ == "__main__":
    unittest.main()
