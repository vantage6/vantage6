import logging
import uuid
from http import HTTPStatus
from unittest.mock import patch

from vantage6.common import logger_name

from vantage6.backend.common import session as db_session

from vantage6.server.model import (
    Collaboration,
    Organization,
    Role,
    Rule,
    User,
)
from vantage6.server.model.rule import Operation, Scope

from .test_resource_base import TestResourceBase

logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):
    def test_user_with_id(self):
        headers = self.login_as_root()
        user = self.create_user()
        result = self.app.get(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, 200)
        user = result.json

        expected_fields = ["username", "roles"]
        for field in expected_fields:
            self.assertIn(field, user)

    def test_user_unknown(self):
        headers = self.login_as_root()
        result = self.app.get("/api/user/9999", headers=headers)
        self.assertEqual(result.status_code, 404)

    @patch("vantage6.server.resource.user.Users._create_user_in_keycloak")
    def test_user_post(self, mock_create_user_in_keycloak):
        mock_create_user_in_keycloak.return_value = str(uuid.uuid1())

        headers = self.login_as_root()
        new_user = {
            "username": "unittest",
            "password": "Super-secret1!",
        }
        result = self.app.post("/api/user", headers=headers, json=new_user)
        self.assertEqual(result.status_code, 201)

        result = self.app.post("/api/user", headers=headers, json=new_user)
        self.assertEqual(result.status_code, 400)

    @patch("vantage6.server.resource.user.User._delete_user_in_keycloak")
    def test_user_delete(self, mock_delete_user_in_keycloak):
        mock_delete_user_in_keycloak.return_value = None

        headers = self.login_as_root()
        user = self.create_user()
        result = self.app.delete(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_user_delete_unknown(self):
        headers = self.login_as_root()
        result = self.app.delete("/api/user/99999", headers=headers)
        self.assertEqual(result.status_code, 404)

    def test_user_patch(self):
        headers = self.login_as_root()
        user = self.create_user()
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={"rules": [1]},
        )
        self.assertEqual(result.status_code, 200)

    def test_user_patch_unknown(self):
        headers = self.login_as_root()
        result = self.app.patch(
            "/api/user/9999", headers=headers, json={"username": "root2"}
        )
        self.assertEqual(result.status_code, 404)

    def test_root_role_forbidden(self):
        headers = self.login_as_root()
        new_user = {
            "username": "some",
            "roles": "this-is-not-a-list-of-ints",
            "password": "super-secret",
        }
        result = self.app.post("/api/user", headers=headers, json=new_user)
        self.assertEqual(result.status_code, 400)

    def test_view_permission_user(self):
        # user not found
        headers = self.get_user_auth_header()
        result = self.app.get("/api/user/9999", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # try to view users without any permissions
        headers = self.get_user_auth_header()
        result = self.app.get("/api/user", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # root user can view all users
        headers = self.login_as_root()
        result, json_data = self.paginated_list("/api/user", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(User.get()))

        # view users of your organization
        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.VIEW)
        org = Organization()
        org.save()
        headers = self.get_user_auth_header(org, rules=[rule])
        result, json_data = self.paginated_list("/api/user", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(org.users))

        # view a single user of your organization
        user_id = org.users[0].id
        result = self.app.get(f"/api/user/{user_id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # user can view their own data. This should always be possible
        user = self.create_user(rules=[])
        headers = self.login(user)
        result = self.app.get(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # collaboration permission - view single user
        org2 = Organization()
        org2.save()
        org3 = Organization()
        org3.save()
        col = Collaboration(organizations=[org2, org3])
        col.save()
        user = self.create_user(organization=org2, rules=[])
        rule = Rule.get_by_("user", scope=Scope.COLLABORATION, operation=Operation.VIEW)
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        result = self.app.get(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # collaboration permission - view list of users
        result = self.app.get("/api/user", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        # expecting 2 users: 1 in org2 and the 1 in org3 which is logged in now
        self.assertEqual(len(result.json["data"]), 2)

        # collaboration permission - viewing outside collaboration should fail
        org_outside_col = Organization()
        org_outside_col.save()
        headers = self.get_user_auth_header(organization=org_outside_col, rules=[rule])
        result = self.app.get(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # collaboration permission - viewing other collaborations should fail
        result = self.app.get(
            "/api/user", headers=headers, query_string={"collaboration_id": col.id}
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # Check that collaboration permission still works if the organization is not
        # actually in a collaboration.
        org4 = Organization()
        org4.save()
        user_org_4 = User(organization=org4)
        user_org_4.save()
        rule = Rule.get_by_("user", Scope.COLLABORATION, Operation.VIEW)
        headers = self.create_user_and_login(organization=org4, rules=[rule])
        result = self.app.get("/api/user", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(result.json["data"]), len(org4.users))

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        org4.delete()
        org_outside_col.delete()
        col.delete()
        user.delete()
        user_org_4.delete()

    def test_bounce_existing_username(self):
        headers = self.get_user_auth_header()
        User(username="something").save()
        userdata = {
            "username": "not-important",
            "password": "welkom01",
        }
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

        userdata["username"] = "not-important"
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

    @patch("vantage6.server.resource.user.Users._create_user_in_keycloak")
    def test_new_permission_user(self, mock_create_user_in_keycloak):
        mock_create_user_in_keycloak.return_value = str(uuid.uuid1())

        userdata = {
            "username": "smarty",
            "password": "Welkom01!",
        }

        # Creating users for other organizations can only be by global scope
        org = Organization()
        org.save()
        other_org = Organization()
        other_org.save()

        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.CREATE)
        userdata["organization_id"] = other_org.id
        headers = self.get_user_auth_header(org, rules=[rule])
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # you can do that when you have the global scope
        gl_rule = Rule.get_by_("user", Scope.GLOBAL, Operation.CREATE)
        userdata["rules"] = [gl_rule.id]
        headers = self.get_user_auth_header(org, rules=[gl_rule])
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # you need to own all rules in order to assign them
        headers = self.get_user_auth_header(org, rules=[rule])
        userdata["username"] = "smarty2"
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test inside the collaboration
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()
        rule = Rule.get_by_(
            "user", scope=Scope.COLLABORATION, operation=Operation.CREATE
        )
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        userdata["username"] = "smarty4"
        userdata["organization_id"] = org2.id
        userdata["rules"] = [rule.id]
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # check outside the collaboration fails
        org3 = Organization()
        org3.save()
        userdata["username"] = "smarty5"
        userdata["organization_id"] = org3.id
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # you can only create users for in which you have all rules
        rule_view_roles = Rule.get_by_("role", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule, rule_view_roles])
        role = Role(rules=[rule], organization=org)
        role.save()
        userdata["username"] = "smarty3"
        userdata["roles"] = [role.id]
        del userdata["organization_id"]
        del userdata["rules"]
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)
        # verify that user has the role
        result = self.app.get(
            "/api/role", headers=headers, query_string={"user_id": result.json["id"]}
        )
        self.assertEqual(len(result.json["data"]), 1)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()
        role.delete()

    def test_patch_user_permissions(self):
        org = Organization()
        org.save()
        user = User(
            username="Username-unique-1",
            keycloak_id=str(uuid.uuid1()),
            organization=org,
        )
        user.save()

        # check non-existing user
        headers = self.get_user_auth_header()
        result = self.app.patch("/api/user/9999", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # patching without permissions
        headers = self.get_user_auth_header()
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={"rules": [1]},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual("Username-unique-1", user.username)

        # patch as a user of other organization
        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.EDIT)
        self.get_user_auth_header(rules=[rule])
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={"rules": [rule.id]},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual("Username-unique-1", user.username)

        # edit other user within your organization
        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.EDIT)
        headers = self.get_user_auth_header(
            organization=user.organization, rules=[rule]
        )
        result = self.app.patch(
            f"/api/user/{user.id}", headers=headers, json={"rules": [rule.id]}
        )
        db_session.session.refresh(user)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(user.rules, [rule])

        # check that password cannot be edited
        rule = Rule.get_by_("user", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.patch(
            f"/api/user/{user.id}", headers=headers, json={"password": "keep-it-safe"}
        )
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

        # edit user from different organization
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={
                "rules": [rule.id],
            },
        )
        db_session.session.refresh(user)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(user.rules, [rule])

        # test editing user inside the collaboration
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()
        rule2 = Rule.get_by_(
            "user", scope=Scope.COLLABORATION, operation=Operation.EDIT
        )
        user.rules = [rule2]
        user.save()
        headers = self.get_user_auth_header(organization=org2, rules=[rule2])
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={
                "rules": [rule2.id],
            },
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # check editing outside the collaboration fails
        org3 = Organization()
        org3.save()
        headers = self.get_user_auth_header(organization=org3, rules=[rule2])
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={
                "rules": [rule2.id],
            },
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test that you cannot assign rules that you not own
        not_owning_rule = Rule.get_by_("user", Scope.OWN, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={"rules": [not_owning_rule.id]},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test that you cannot assign role that has rules that you do not own
        role = Role(name="somename", rules=[not_owning_rule], organization=org)
        role.save()
        result = self.app.patch(
            f"/api/user/{user.id}", headers=headers, json={"roles": [role.id]}
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test that you CAN assign rules if you have higher permissions than
        # the user you are assigning rules to. In this case, the user being
        # changed only has permission to edit their own user, while the actor
        # has global permission for that
        headers = self.get_user_auth_header(rules=[rule, not_owning_rule])
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={"rules": [not_owning_rule.id, rule.id]},
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test that you cannot assign rules to users if they have permissions
        # that you don't have yourself
        second_not_owning_rule = Rule.get_by_(
            "node", Scope.ORGANIZATION, Operation.EDIT
        )
        user.rules.append(second_not_owning_rule)
        user.save()
        headers = self.get_user_auth_header(rules=[rule, not_owning_rule])
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={"rules": [not_owning_rule.id, rule.id]},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test that you CAN change the rules. To do so, a user is generated
        # that has same rules as current user, but also rule to edit other
        # users and another one current user does not possess
        # get rules not by copying object to prevent invalid DB state
        assigning_user_rules = [Rule.get(rule.id) for rule in user.rules]
        assigning_user_rules.append(
            Rule.get_by_("user", Scope.GLOBAL, Operation.EDIT),
        )
        assigning_user_rules.append(not_owning_rule)

        headers = self.get_user_auth_header(rules=assigning_user_rules)
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={"rules": [not_owning_rule.id, rule.id]},
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)

        result = self.app.get(
            "/api/rule", headers=headers, query_string={"user_id": user.id}
        )
        user_rule_ids = [rule["id"] for rule in result.json.get("data")]
        self.assertIn(not_owning_rule.id, user_rule_ids)

        # test that you cannot assign roles if you don't have all the
        # permissions for that role yourself (even though you have permission
        # to assign roles)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.patch(
            f"/api/user/{user.id}", headers=headers, json={"roles": [role.id]}
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test that you CAN assign roles
        rule_global_view = Rule.get_by_("role", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(
            rules=[rule, not_owning_rule, rule_global_view]
        )
        result = self.app.patch(
            f"/api/user/{user.id}", headers=headers, json={"roles": [role.id]}
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)

        result = self.app.get(
            "/api/role", headers=headers, query_string={"user_id": user.id}
        )
        user_role_ids = [role["id"] for role in result.json.get("data")]
        self.assertIn(role.id, user_role_ids)

        # test that you CANNOT assign roles from different organization
        other_org_role = Role(
            name="somename", rules=[not_owning_rule], organization=Organization()
        )
        other_org_role.save()
        headers = self.get_user_auth_header(rules=[rule, not_owning_rule])
        result = self.app.patch(
            f"/api/user/{user.id}", headers=headers, json={"roles": [other_org_role.id]}
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test missing role
        result = self.app.patch(
            f"/api/user/{user.id}", headers=headers, json={"roles": [9999]}
        )
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # test missing rule
        result = self.app.patch(
            f"/api/user/{user.id}", headers=headers, json={"rules": [9999]}
        )
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        user.delete()
        role.delete()
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()

    @patch("vantage6.server.resource.user.User._delete_user_in_keycloak")
    def test_delete_user_permissions(self, mock_delete_user_in_keycloak):
        mock_delete_user_in_keycloak.return_value = None
        org = Organization()
        user = User(
            username="Username",
            organization=org,
            keycloak_id=str(uuid.uuid4()),
        )
        user.save()

        # check non-exsitsing user
        headers = self.get_user_auth_header()
        result = self.app.delete("/api/user/9999", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # try to delete without any permissions
        headers = self.get_user_auth_header()
        result = self.app.delete(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # same organization but missing permissions
        rule = Rule.get_by_("user", Scope.OWN, Operation.DELETE)
        headers = self.get_user_auth_header(
            organization=user.organization, rules=[rule]
        )
        result = self.app.delete(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # other organization with organization scope
        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.DELETE)
        headers = self.get_user_auth_header(organization=Organization(), rules=[rule])
        result = self.app.delete(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # delete yourself
        rule = Rule.get_by_("user", Scope.OWN, Operation.DELETE)
        user.rules.append(rule)
        user.save()
        headers = self.login(user)
        result = self.app.delete(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        # User is deleted by the endpoint! user.delete()

        # delete colleague
        user = User(
            username="Username",
            organization=Organization(),
        )
        user.save()
        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.DELETE)
        headers = self.get_user_auth_header(
            rules=[rule], organization=user.organization
        )
        result = self.app.delete(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        # User is deleted by the endpoint user.delete()

        # delete as root
        user = User(
            username="Username",
            organization=Organization(),
        )
        user.save()
        rule = Rule.get_by_("user", Scope.GLOBAL, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.delete(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        # user is deleted by endpoint! user.delete()

        # check delete outside the collaboration fails
        user = User(
            username="Username",
            organization=org,
        )
        user.save()
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()
        org3 = Organization()
        org3.save()
        rule = Rule.get_by_("user", Scope.COLLABORATION, Operation.DELETE)
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        result = self.app.delete(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test delete inside the collaboration
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        result = self.app.delete(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()
