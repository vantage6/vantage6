import logging
import json
import uuid
from http import HTTPStatus
from unittest.mock import MagicMock, patch

from vantage6.common import logger_name
from vantage6.common.enum import RunStatus
from vantage6.common.serialization import serialize
from vantage6.common import bytes_to_base64s
from vantage6.backend.common import session as db_session
from vantage6.server.model import (
    Rule,
    Role,
    Organization,
    User,
    Node,
    Collaboration,
    Task,
    Run,
    AlgorithmStore,
    Study,
    Session,
    Dataframe,
)
from vantage6.server.model.rule import Scope, Operation
from vantage6.server._version import __version__
from .test_resource_base import TestResourceBase


logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):

    def test_version(self):
        rv = self.app.get("/api/version")
        r = json.loads(rv.data)
        self.assertIn("version", r)
        self.assertEqual(r["version"], __version__)

    def test_token_different_users(self):
        for type_ in ["root", "admin", "user"]:
            tokens = self.app.post("/api/token/user", json=self.credentials[type_]).json
            self.assertIn("access_token", tokens)
            self.assertIn("refresh_token", tokens)

    def test_organization(self):
        rule = Rule.get_by_("organization", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])

        # First retrieve a list of all organizations
        _response, orgs = self.paginated_list("/api/organization", headers)
        self.assertEqual(len(orgs), len(Organization.get()))

        attrs = [
            "id",
            "name",
            "domain",
            "name",
            "address1",
            "address2",
            "zipcode",
            "country",
        ]

        org = orgs[0]
        for attr in attrs:
            self.assertIn(attr, org)

        # Retrieve a single organization
        url = f'/api/organization/{org["id"]}'
        org = self.app.get(url, headers=headers).json
        self.assertEqual(org["id"], orgs[0]["id"])
        self.assertEqual(org["name"], orgs[0]["name"])

        # Create a new organization
        org_details = {"name": "Umbrella Corporation", "address1": "Resident Evil Pike"}

        org = self.app.post("/api/organization", json=org_details, headers=headers).json

        # for attr in attrs:
        #     self.assertIn(attr, org)

        # self.assertGreater(org['id'], 0)

        orgs = self.app.get("/api/organization", headers=headers).json
        # self.assertEqual(len(orgs), 4)

    def test_collaboration(self):
        org = Organization()
        rule_view = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.VIEW)
        rule_create = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.CREATE)
        headers = self.get_user_auth_header(
            organization=org, rules=[rule_view, rule_create]
        )

        collaborations = self.app.get("/api/collaboration", headers=headers)
        self.assertEqual(collaborations.status_code, HTTPStatus.OK)
        db_cols = Collaboration.get()
        self.assertEqual(len(collaborations.json["data"]), len(db_cols))

        # Create a new collaboration
        col_details = {
            "name": "New Collaboration",
            "organization_ids": [org.id],
            "encrypted": True,
            "session_restrict_to_same_image": True,
        }

        response = self.app.post(
            "/api/collaboration", json=col_details, headers=headers
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_node_without_id(self):
        # GET
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        nodes = self.app.get("/api/node", headers=headers).json["data"]
        expected_fields = [
            "name",
            "collaboration",
            "organization",
            "status",
            "id",
            "type",
            "last_seen",
            "ip",
        ]
        for node in nodes:
            for key in expected_fields:
                self.assertIn(key, node)

        nodes = self.app.get("/api/node", headers=headers).json
        self.assertIsNotNone(nodes)

        # POST
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.CREATE)
        headers = self.get_user_auth_header(rules=[rule])
        # unknown collaboration id should fail
        response = self.app.post(
            "/api/node", headers=headers, json={"collaboration_id": 99999}
        )
        response_json = response.json
        self.assertIn("msg", response_json)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # succesfully create a node
        org = Organization(name=str(uuid.uuid1()))
        col = Collaboration(organizations=[org])
        col.save()

        headers = self.get_user_auth_header(org, rules=[rule])
        response = self.app.post(
            "/api/node", headers=headers, json={"collaboration_id": col.id}
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

    def test_node_with_id(self):
        # root user can access all nodes
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        node = self.app.get("/api/node/8", headers=headers).json
        expected_fields = [
            "name",
            "collaboration",
            "organization",
            "status",
            "id",
            "type",
            "last_seen",
            "ip",
        ]
        for key in expected_fields:
            self.assertIn(key, node)

        # user cannot access all
        headers = self.get_user_auth_header()
        node = self.app.get("/api/node/8", headers=headers)
        self.assertEqual(node.status_code, HTTPStatus.UNAUTHORIZED)

        # some nodes just don't exist
        node = self.app.get("/api/node/9999", headers=headers)
        self.assertEqual(node.status_code, 404)

    def test_result_with_id(self):
        # TODO improve this unit test to create its own task and run
        headers = self.login("root")
        run = self.app.get("/api/run/1", headers=headers)
        self.assertEqual(run.status_code, 200)

        run = self.app.get("/api/run/1?include=task", headers=headers)
        self.assertEqual(run.status_code, 200)

    def test_run_without_id(self):
        headers = self.login("root")
        result1 = self.app.get("/api/run", headers=headers)
        self.assertEqual(result1.status_code, 200)

        result2 = self.app.get("/api/run?state=open", headers=headers)
        self.assertEqual(result2.status_code, 200)

        result3 = self.app.get("/api/run?task_id=1", headers=headers)
        self.assertEqual(result3.status_code, 200)

    def test_task_with_id(self):
        headers = self.login("root")
        result = self.app.get("/api/task/1", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_task_witout_id(self):
        headers = self.login("root")
        result = self.app.get("/api/task", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_task_including_runs(self):
        headers = self.login("root")
        result = self.app.get("/api/task?include=runs", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_task_unknown(self):
        headers = self.login("root")
        result = self.app.get("/api/task/9999", headers=headers)
        self.assertEqual(result.status_code, 404)

    def test_user_with_id(self):
        headers = self.login("admin")
        result = self.app.get("/api/user/1", headers=headers)
        self.assertEqual(result.status_code, 200)
        user = result.json

        expected_fields = ["username", "firstname", "lastname", "roles"]
        for field in expected_fields:
            self.assertIn(field, user)

    def test_user_unknown(self):
        headers = self.login("admin")
        result = self.app.get("/api/user/9999", headers=headers)
        self.assertEqual(result.status_code, 404)

    def test_user_without_id(self):
        for role in ["user", "admin", "root"]:
            headers = self.login(role)
            result = self.app.get("/api/user", headers=headers)
            self.assertEqual(result.status_code, 200)

    def test_user_post(self):
        headers = self.login("root")
        new_user = {
            "username": "unittest",
            "firstname": "unit",
            "lastname": "test",
            "email": "unit@test.org",
        }
        # with a bad password, user should not be created
        new_user["password"] = "1234"
        result = self.app.post("/api/user", headers=headers, json=new_user)
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

        new_user["password"] = "Welkom01!"
        result = self.app.post("/api/user", headers=headers, json=new_user)
        self.assertEqual(result.status_code, 201)

        result = self.app.post("/api/user", headers=headers, json=new_user)
        self.assertEqual(result.status_code, 400)

    def test_user_delete(self):
        headers = self.login("root")
        result = self.app.delete("/api/user/5", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_user_delete_unknown(self):
        headers = self.login("root")
        result = self.app.delete("/api/user/99999", headers=headers)
        self.assertEqual(result.status_code, 404)

    def test_user_patch(self):
        headers = self.login("root")
        result = self.app.patch(
            "/api/user/2",
            headers=headers,
            json={"firstname": "Henk", "lastname": "Martin"},
        )
        self.assertEqual(result.status_code, 200)

    def test_user_patch_unknown(self):
        headers = self.login("root")
        result = self.app.patch(
            "/api/user/9999", headers=headers, json={"username": "root2"}
        )
        self.assertEqual(result.status_code, 404)

    def test_root_role_forbidden(self):
        headers = self.login("root")
        new_user = {
            "username": "some",
            "firstname": "guy",
            "lastname": "there",
            "roles": "root",
            "password": "super-secret",
        }
        result = self.app.post("/api/user", headers=headers, json=new_user)
        self.assertEqual(result.status_code, 400)

    @patch("vantage6.backend.common.mail_service.MailService.send_email")
    def test_reset_password(self, send_email):
        user_ = {"username": "root"}
        result = self.app.post("/api/recover/lost", json=user_)
        self.assertEqual(result.status_code, 200)

    @patch("vantage6.backend.common.mail_service.MailService.send_email")
    def test_reset_password_missing_error(self, send_email):
        result = self.app.post("/api/recover/lost", json={})
        self.assertEqual(result.status_code, 400)

    @patch("vantage6.server.resource.recover.decode_token")
    def test_recover_password(self, decode_token):
        decode_token.return_value = {"sub": {"id": 1}}
        new_password = {"password": "$Ecret88!", "reset_token": "token"}
        result = self.app.post("/api/recover/reset", json=new_password)
        self.assertEqual(result.status_code, 200)

        # verify that the new password works
        result = self.app.post(
            "/api/token/user", json={"username": "root", "password": "$Ecret88!"}
        )
        self.assertIn("access_token", result.json)
        self.credentials["root"]["password"] = "$Ecret88!"

    def test_fail_recover_password(self):
        result = self.app.post("/api/recover/reset", json={})
        self.assertEqual(result.status_code, 400)

    def test_change_password(self):
        user = self.create_user(password="Password1!")
        headers = self.login(user.username)

        # test if fails when not providing correct data
        result = self.app.patch(
            "/api/password/change",
            headers=headers,
            json={"current_password": "Password1!"},
        )
        self.assertEqual(result.status_code, 400)
        result = self.app.patch(
            "/api/password/change",
            headers=headers,
            json={"new_password": "a_new_password"},
        )
        self.assertEqual(result.status_code, 400)

        # test if fails when wrong password is provided
        result = self.app.patch(
            "/api/password/change",
            headers=headers,
            json={
                "current_password": "Wrong_password1!",
                "new_password": "A_new_password1!",
            },
        )
        self.assertEqual(result.status_code, 401)

        # test if fails when new password is the same
        result = self.app.patch(
            "/api/password/change",
            headers=headers,
            json={"current_password": "Password1!", "new_password": "Password1!"},
        )
        self.assertEqual(result.status_code, 400)

        # test if it works when used as intended
        result = self.app.patch(
            "/api/password/change",
            headers=headers,
            json={"current_password": "Password1!", "new_password": "A_new_password1"},
        )
        self.assertEqual(result.status_code, 200)
        db_session.session.refresh(user)
        self.assertTrue(user.check_password("A_new_password1"))

    def test_view_rules(self):
        headers = self.login("root")
        result = self.app.get("/api/rule", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_view_roles(self):
        headers = self.login("root")
        result = self.app.get("/api/role", headers=headers)
        self.assertEqual(result.status_code, 200)

        body = result.json["data"]
        expected_fields = ["organization", "name", "description", "users"]
        for field in expected_fields:
            self.assertIn(field, body[0])

    def test_view_role_permissions(self):
        org = Organization()
        org.save()
        other_org = Organization()
        other_org.save()
        col = Collaboration(organizations=[org, other_org])
        col.save()
        org_outside_collab = Organization()
        org_outside_collab.save()

        # non-existing role
        headers = self.login("root")
        result = self.app.get("/api/role/9999", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # root user can view all roles
        result, json_data = self.paginated_list("/api/role", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(Role.get()))

        role = Role(organization=org)
        role.save()

        # without permissions should allow you to view your own roles, which
        # in this case is an empty list
        headers = self.get_user_auth_header()
        result, json_data = self.paginated_list("/api/role", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), 0)

        # view roles of your organization
        rule = Rule.get_by_("role", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule])
        result, json_data = self.paginated_list("/api/role", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # +3 for the root, container and node roles (other default roles are
        # not generated for unit tests)
        self.assertEqual(len(json_data), len(org.roles) + 3)

        # view a single role of your organization
        result = self.app.get(f"/api/role/{role.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # check that user of other organization cannot view roles with
        # organization scope
        headers = self.get_user_auth_header(other_org, rules=[rule])
        result = self.app.get(
            "/api/role", headers=headers, query_string={"organization_id": org.id}
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # user can view their own roles. This should always be possible
        user = self.create_user(rules=[])
        headers = self.login(user.username)
        result = self.app.get(
            "/api/role", headers=headers, query_string={"user_id": user.id}
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # collaboration permission - in same collaboration with id
        rule = Rule.get_by_("role", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(other_org, rules=[rule])
        result = self.app.get(f"/api/role/{role.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # collaboration permission - in same collaboration without id
        result, json_data = self.paginated_list("/api/role", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        # +3 for the root, container and node roles (other default roles are
        # not generated for unit tests)
        self.assertEqual(
            len(json_data),
            len([role_ for org in col.organizations for role_ in org.roles]) + 3,
        )

        # collaboration permission - in different collaboration with id
        headers = self.get_user_auth_header(org_outside_collab, rules=[rule])
        result = self.app.get(f"/api/role/{role.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # collaboration permission - in different collaboration without id
        result = self.app.get(
            "/api/role", headers=headers, query_string={"collaboration_id": col.id}
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        org.delete()
        other_org.delete()
        org_outside_collab.delete()
        col.delete()
        role.delete()
        user.delete()

    def test_create_role_as_root(self):
        headers = self.login("root")

        # obtain available rules
        rules = self.app.get(
            "/api/rule", headers=headers, query_string={"no_pagination": 1}
        ).json["data"]
        rule_ids = [rule.get("id") for rule in rules]

        # assign first two rules to role
        ROLE_TO_CREATE_NAME = "some-role-name"
        body = {
            "name": ROLE_TO_CREATE_NAME,
            "description": "Testing if we can create a role",
            "rules": rule_ids[:2],
        }

        # create role
        result = self.app.post("/api/role", headers=headers, json=body)

        # check that server responded ok
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # verify the values
        self.assertEqual(result.json.get("name"), body["name"])
        self.assertEqual(result.json.get("description"), body["description"])
        result = self.app.get(
            "/api/rule",
            headers=headers,
            query_string={"role_id": result.json.get("id")},
        )
        self.assertEqual(len(result.json.get("data")), 2)

        # cleanup
        for resource in Role.get():
            if resource.name == ROLE_TO_CREATE_NAME:
                resource.delete()

    def test_create_role_as_root_for_different_organization(self):
        headers = self.login("root")

        # obtain available rules
        rules = self.app.get(
            "/api/rule", headers=headers, query_string={"no_pagination": 1}
        ).json["data"]
        # create new organization, so we're sure that the current user
        # is not assigned to the same organization
        org = Organization(name="Some-random-organization")
        org.save()

        ROLE_TO_CREATE_NAME = "some-role-name"
        body = {
            "name": ROLE_TO_CREATE_NAME,
            "description": "Testing if we can create a rol for another org",
            "rules": [rule.get("id") for rule in rules],
            "organization_id": org.id,
        }

        # create role
        result = self.app.post("/api/role", headers=headers, json=body)

        # check that server responded ok
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # verify the organization
        self.assertEqual(org.id, result.json["organization"]["id"])

        # cleanup
        for resource in Role.get():
            if resource.name == ROLE_TO_CREATE_NAME:
                resource.delete()

    def test_create_role_permissions(self):
        all_rules = Rule.get()

        # check user without any permissions
        headers = self.get_user_auth_header()

        ROLE_TO_CREATE_NAME = "some-role-name"
        body = {
            "name": ROLE_TO_CREATE_NAME,
            "description": "Testing if we can create a role for another org",
            "rules": [rule.id for rule in all_rules],
        }
        result = self.app.post("/api/role", headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # check that user with a missing rule cannot create a role with that
        # missing rule. Note that we specifically remove a rule with the global scope
        # because if a user misses a rule with collaboration or organization scope,
        # but has the global scope, they can still create roles wih the missing rule.
        rules = all_rules
        for rule in rules:
            if rule.scope == Scope.GLOBAL:
                rules.remove(rule)
                break
        headers = self.get_user_auth_header(rules=rules)
        result = self.app.post("/api/role", headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # check that user can create role within his organization
        rule = Rule.get_by_(
            "role", scope=Scope.ORGANIZATION, operation=Operation.CREATE
        )

        headers = self.get_user_auth_header(rules=[rule])
        body["rules"] = [rule.id]
        result = self.app.post("/api/role", headers=headers, json=body)

        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # check a non-existing organization
        headers = self.login("root")
        body["organization_id"] = 9999
        result = self.app.post("/api/role", headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # check that assigning an unexisting rule is not possible
        headers = self.get_user_auth_header()
        body["rules"] = [9999]
        result = self.app.post("/api/role", headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # check creating role inside the collaboration
        org1 = Organization()
        org1.save()
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org1, org2])
        col.save()
        rule = Rule.get_by_(
            "role", scope=Scope.COLLABORATION, operation=Operation.CREATE
        )
        headers = self.get_user_auth_header(organization=org1, rules=[rule])
        body["rules"] = [rule.id]
        body["organization_id"] = org2.id
        result = self.app.post("/api/role", headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # check creating role outside the collaboration fails
        org3 = Organization()
        org3.save()
        body["organization_id"] = org3.id
        result = self.app.post("/api/role", headers=headers, json=body)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        for resource in Role.get():
            if resource.name == ROLE_TO_CREATE_NAME:
                resource.delete()

    def test_edit_role(self):
        headers = self.login("root")

        # create testing entities
        org = Organization(name="some-organization-name")
        org.save()
        role = Role(name="some-role-name", organization=org)
        role.save()

        # test name, description
        result = self.app.patch(
            f"/api/role/{role.id}",
            headers=headers,
            json={
                "name": "a-different-role-name",
                "description": "some description of this role...",
            },
        )

        db_session.session.refresh(role)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(role.name, "a-different-role-name")
        self.assertEqual(role.description, "some description of this role...")

        # test modifying rules
        all_rule_ids = [rule.id for rule in Rule.get()]
        result = self.app.patch(
            f"/api/role/{role.id}", headers=headers, json={"rules": all_rule_ids}
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertListEqual(all_rule_ids, [rule.id for rule in role.rules])

        # test non owning rules
        rule = Rule.get_by_("role", Scope.ORGANIZATION, Operation.EDIT)
        headers = self.get_user_auth_header(org, [rule])
        result = self.app.patch(
            f"/api/role/{role.id}", headers=headers, json={"rules": all_rule_ids}
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test modifying role of another organization, without global
        # permission
        org2 = Organization(name="another-organization")
        headers = self.get_user_auth_header(org2, [rule])
        result = self.app.patch(
            f"/api/role/{role.id}",
            headers=headers,
            json={"name": "this-will-not-be-updated"},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test modifying role with global permissions
        rule = Rule.get_by_("role", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(org2, [rule])
        result = self.app.patch(
            f"/api/role/{role.id}",
            headers=headers,
            json={"name": "this-will-not-be-updated"},
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test editing role inside the collaboration
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()
        rule = Rule.get_by_("role", scope=Scope.COLLABORATION, operation=Operation.EDIT)
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        result = self.app.patch(
            f"/api/role/{role.id}",
            headers=headers,
            json={
                "name": "new-role-name",
            },
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # check editing role outside the collaboration fails
        org3 = Organization()
        org3.save()
        role = Role(name="some-role-name", organization=org3)
        role.save()
        result = self.app.patch(
            f"/api/role/{role.id}",
            headers=headers,
            json={"name": "this-will-not-be-updated"},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

    def test_remove_role(self):
        org = Organization()
        org.save()
        role = Role(organization=org)
        role.save()

        # test removal without permissions
        headers = self.get_user_auth_header()
        result = self.app.delete(f"/api/role/{role.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test removal with organization permissions
        rule = Rule.get_by_("role", Scope.ORGANIZATION, Operation.DELETE)
        headers = self.get_user_auth_header(org, [rule])
        result = self.app.delete(f"/api/role/{role.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test failed removal with organization permissions
        role = Role(organization=org)  # because we removed it...
        role.save()
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.delete(f"/api/role/{role.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test removal with global permissions
        rule = Rule.get_by_("role", Scope.GLOBAL, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.delete(f"/api/role/{role.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # check removing role outside the collaboration fails
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()
        role = Role(organization=org)  # because we removed it...
        role.save()

        org3 = Organization()
        org3.save()
        rule = Rule.get_by_("role", Scope.COLLABORATION, Operation.DELETE)
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        result = self.app.delete(f"/api/role/{role.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test removing role inside the collaboration
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        result = self.app.delete(f"/api/role/{role.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # cleanup
        org3.delete()
        org2.delete()
        org.delete()
        col.delete()

    def test_add_single_rule_to_role(self):
        headers = self.login("root")

        role = Role(name="empty", organization=Organization())
        role.save()

        # role without rules
        result, json_data = self.paginated_list(
            f"/api/rule?role_id={role.id}", headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), 0)

        rule = Rule.get()[0]

        # try to add rule to non existing role
        result = self.app.post(f"/api/role/9999/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # try to add non existent rule
        result = self.app.post(f"/api/role/{role.id}/rule/9999", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # add a rule to a role
        result = self.app.post(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # check that the role now has one rule
        result, json_data = self.paginated_list(
            f"/api/rule?role_id={role.id}", headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), 1)

    def test_remove_single_rule_from_role(self):
        headers = self.login("root")

        rule = Rule.get()[0]
        role = Role(name="unit", organization=Organization(), rules=[rule])
        role.save()

        # try to add rule to non existing role
        result = self.app.delete(f"/api/role/9999/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # try to add non existent rule
        result = self.app.delete(f"/api/role/{role.id}/rule/9999", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        result, json_data = self.paginated_list(
            f"/api/rule?role_id={role.id}", headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), 1)

        result = self.app.delete(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(result.json), 0)

    def test_add_rule_to_role_permission(self):
        org = Organization()
        org.save()
        role = Role(name="new-role", organization=org)
        role.save()

        rule = Rule.get_by_("role", Scope.ORGANIZATION, Operation.EDIT)

        # try adding a rule without any permission
        headers = self.get_user_auth_header()
        result = self.app.post(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # you cant edit other organizations roles
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.post(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # you can edit other organizations with the global permission
        rule = Rule.get_by_("role", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.post(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # you can only rules that are lower in hierarchy than the ones you own
        rule = Rule.get_by_("role", Scope.ORGANIZATION, Operation.EDIT)
        result = self.app.post(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # you can't assign rules you don't own
        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.EDIT)
        result = self.app.post(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test inside the collaboration
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()
        rule = Rule.get_by_("role", scope=Scope.COLLABORATION, operation=Operation.EDIT)
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        result = self.app.post(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # check outside the collaboration fails
        org3 = Organization()
        org3.save()
        role2 = Role(name="some-role-name", organization=org3)
        role2.save()
        result = self.app.post(f"/api/role/{role2.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        role.delete()
        role2.delete()
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()

    def test_remove_rule_from_role_permissions(self):
        org = Organization()
        org.save()
        role = Role(name="new-role", organization=org)
        role.save()
        rule = Rule.get_by_("role", Scope.ORGANIZATION, Operation.EDIT)

        # try removing without any permissions
        headers = self.get_user_auth_header()
        result = self.app.delete(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # try removing rule from other organization
        headers = self.get_user_auth_header(organization=Organization(), rules=[rule])
        result = self.app.delete(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # try removing rule which is not in the role
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        result = self.app.delete(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        role.rules = [rule]
        role.save()

        # lets try that again
        headers = self.get_user_auth_header(
            organization=role.organization, rules=[rule]
        )
        result = self.app.delete(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # add rule back again
        role.rules = [rule]
        role.save()

        # power users can edit other organization rules
        power_rule = Rule.get_by_("role", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[power_rule, rule])
        result = self.app.delete(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test inside the collaboration
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()
        rule = Rule.get_by_("role", scope=Scope.COLLABORATION, operation=Operation.EDIT)
        role.rules.append(rule)
        role.save()
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        result = self.app.delete(f"/api/role/{role.id}/rule/{rule.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # check outside the collaboration fails
        org3 = Organization()
        org3.save()
        role2 = Role(name="some-role-name", organization=org3)
        role2.rules.append(rule)
        role2.save()
        result = self.app.delete(
            f"/api/role/{role2.id}/rule/{rule.id}", headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        db_session.session.refresh(role)
        role.delete()
        role2.delete()
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()

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
        headers = self.login("root")
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
        headers = self.login(user.username)
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

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        org_outside_col.delete()
        col.delete()
        user.delete()

    def test_bounce_existing_username_and_email(self):
        headers = self.get_user_auth_header()
        User(username="something", email="mail@me.org").save()
        userdata = {
            "username": "not-important",
            "firstname": "name",
            "lastname": "lastname",
            "password": "welkom01",
            "email": "mail@me.org",
        }
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

        userdata["username"] = "not-important"
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

    def test_new_permission_user(self):
        userdata = {
            "username": "smarty",
            "firstname": "Smart",
            "lastname": "Pants",
            "password": "Welkom01!",
            "email": "mail-us@me.org",
        }

        # Creating users for other organizations can only be by global scope
        org = Organization()
        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.CREATE)
        userdata["organization_id"] = 1
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
        userdata["email"] = "mail2@me.org"
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
        userdata["email"] = "mail4@me.org"
        userdata["organization_id"] = org2.id
        userdata["rules"] = [rule.id]
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # check outside the collaboration fails
        org3 = Organization()
        org3.save()
        userdata["username"] = "smarty5"
        userdata["email"] = "mail5@me.org"
        userdata["organization_id"] = org3.id
        result = self.app.post("/api/user", headers=headers, json=userdata)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # you can only create users for in which you have all rules
        rule_view_roles = Rule.get_by_("role", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule, rule_view_roles])
        role = Role(rules=[rule], organization=org)
        role.save()
        userdata["username"] = "smarty3"
        userdata["email"] = "mail3@me.org"
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
            firstname="Firstname",
            lastname="Lastname",
            username="Username-unique-1",
            password="Password",
            email="a@b.c2",
            organization=org,
        )
        user.save()
        self.credentials[user.username] = {
            "username": user.username,
            "password": "Password",
        }

        # check non-existing user
        headers = self.get_user_auth_header()
        result = self.app.patch("/api/user/9999", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # patching without permissions
        headers = self.get_user_auth_header()
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={"firstname": "this-aint-gonna-fly"},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual("Username-unique-1", user.username)

        # patch as a user of other organization
        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.EDIT)
        self.get_user_auth_header(rules=[rule])
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={"firstname": "this-aint-gonna-fly"},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual("Username-unique-1", user.username)

        # patch as another user from the same organization
        rule = Rule.get_by_("user", Scope.OWN, Operation.EDIT)
        self.get_user_auth_header(user.organization, [rule])
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={"firstname": "this-aint-gonna-fly"},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual("Username-unique-1", user.username)

        # edit 'simple' fields
        rule = Rule.get_by_("user", Scope.OWN, Operation.EDIT)
        user.rules.append(rule)
        user.save()
        headers = self.login(user.username)
        result = self.app.patch(
            f"/api/user/{user.id}", headers=headers, json={"firstname": "yeah"}
        )
        db_session.session.refresh(user)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual("yeah", user.firstname)

        # edit other user within your organization
        rule = Rule.get_by_("user", Scope.ORGANIZATION, Operation.EDIT)
        headers = self.get_user_auth_header(
            organization=user.organization, rules=[rule]
        )
        result = self.app.patch(
            f"/api/user/{user.id}", headers=headers, json={"firstname": "whatever"}
        )
        db_session.session.refresh(user)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual("whatever", user.firstname)

        # check that password cannot be edited
        rule = Rule.get_by_("user", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.patch(
            f"/api/user/{user.id}", headers=headers, json={"password": "keep-it-safe"}
        )
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

        # edit user from different organization, and test other edit fields
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={
                "firstname": "again",
                "lastname": "and again",
            },
        )
        db_session.session.refresh(user)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual("again", user.firstname)
        self.assertEqual("and again", user.lastname)

        # test editing user inside the collaboration
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()
        rule2 = Rule.get_by_(
            "user", scope=Scope.COLLABORATION, operation=Operation.EDIT
        )
        headers = self.get_user_auth_header(organization=org2, rules=[rule2])
        result = self.app.patch(
            f"/api/user/{user.id}",
            headers=headers,
            json={
                "firstname": "something",
                "lastname": "everything",
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
                "firstname": "will-not-work",
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

    def test_delete_user_permissions(self):
        org = Organization()
        user = User(
            firstname="Firstname",
            lastname="Lastname",
            username="Username",
            password="Password",
            email="a@b.c",
            organization=org,
        )
        user.save()
        self.credentials[user.username] = {
            "username": user.username,
            "password": "Password",
        }

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
        headers = self.login(user.username)
        result = self.app.delete(f"/api/user/{user.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        # User is deleted by the endpoint! user.delete()

        # delete colleague
        user = User(
            firstname="Firstname",
            lastname="Lastname",
            username="Username",
            password="Password",
            email="a@b.c",
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
            firstname="Firstname",
            lastname="Lastname",
            username="Username",
            password="Password",
            email="a@b.c",
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
            firstname="Firstname",
            lastname="Lastname",
            username="Username",
            password="Password",
            email="a@b.c",
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

    def test_view_organization_as_user_permissions(self):
        # view without any permissions
        headers = self.get_user_auth_header()
        result = self.app.get("/api/organization", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # view your own organization
        rule = Rule.get_by_("organization", Scope.ORGANIZATION, Operation.VIEW)
        user = self.create_user(rules=[rule])
        headers = self.login(user.username)
        result = self.app.get(
            f"/api/organization/{user.organization.id}", headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # try to view another organization without permission
        org = Organization()
        org.save()
        result = self.app.get(f"/api/organization/{org.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # Missing organization with global view
        rule = Rule.get_by_("organization", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.get("/api/organization/9999", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # test global view
        result = self.app.get(f"/api/organization/{org.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test view inside the collaboration
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()
        rule = Rule.get_by_(
            "organization", scope=Scope.COLLABORATION, operation=Operation.VIEW
        )
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        result = self.app.get(f"/api/organization/{org.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # check view outside the collaboration fails
        org3 = Organization()
        org3.save()
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        result = self.app.get(f"/api/organization/{org.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()

    def test_view_organization_as_node_permission(self):
        node, api_key = self.create_node()
        headers = self.login_node(api_key)

        # test list organization with only your organization
        result = self.app.get("/api/organization", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(result.json["data"][0]["id"], node.organization.id)

        # test list organization
        result = self.app.get(
            f"/api/organization/{node.organization.id}", headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(result.json["id"], node.organization.id)
        node.delete()

    def test_view_organization_as_container_permission(self):
        node, api_key = self.create_node()
        headers = self.login_container(node=node, api_key=api_key)

        # try to get organization where he runs
        result = self.app.get(
            f"/api/organization/{node.organization.id}", headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(result.json["id"], node.organization.id)

        # get all organizations in the collaboration
        result = self.app.get("/api/organization", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertIsInstance(result.json["data"], list)

        # cleanup
        node.delete()

    def test_create_organization_permissions(self):
        # try creating an organization without permissions
        headers = self.get_user_auth_header()
        result = self.app.post(
            "/api/organization",
            headers=headers,
            json={"name": "this-aint-gonna-happen"},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # create an organization
        ORG_CREATED_NAME = "this-is-gonna-happen"
        rule = Rule.get_by_("organization", Scope.GLOBAL, Operation.CREATE)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.post(
            "/api/organization", headers=headers, json={"name": ORG_CREATED_NAME}
        )
        self.assertEqual(result.status_code, HTTPStatus.CREATED)
        self.assertIsNotNone(Organization.get_by_name(ORG_CREATED_NAME))

        # cleanup
        for resource in Organization.get():
            if resource.name == ORG_CREATED_NAME:
                resource.delete()

    def test_patch_organization_permissions(self):
        # unknown organization
        headers = self.get_user_auth_header()
        results = self.app.patch("/api/organization/9999", headers=headers, json={})
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # try to change anything without permissions
        org = Organization(name="first-name")
        org.save()
        results = self.app.patch(
            f"/api/organization/{org.id}", headers=headers, json={}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # change as super user
        rule = Rule.get_by_("organization", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.patch(
            f"/api/organization/{org.id}", headers=headers, json={"name": "second-name"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "second-name")

        # change as organization editor
        rule = Rule.get_by_("organization", Scope.ORGANIZATION, Operation.EDIT)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.patch(
            f"/api/organization/{org.id}", headers=headers, json={"name": "third-name"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "third-name")

        # change other organization as organization editor
        rule = Rule.get_by_("organization", Scope.ORGANIZATION, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.patch(
            f"/api/organization/{org.id}", headers=headers, json={"name": "third-name"}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test editing organization inside the collaboration
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()
        rule2 = Rule.get_by_(
            "organization", scope=Scope.COLLABORATION, operation=Operation.EDIT
        )
        headers = self.get_user_auth_header(organization=org2, rules=[rule2])
        results = self.app.patch(
            f"/api/organization/{org.id}", headers=headers, json={"name": "fourth-name"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # check editing outside the collaboration fails
        org3 = Organization()
        org3.save()
        headers = self.get_user_auth_header(organization=org3, rules=[rule2])
        results = self.app.patch(
            f"/api/organization/{org.id}",
            headers=headers,
            json={"name": "not-going-to-happen"},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

    def test_organization_view_nodes(self):
        # create organization, collaboration and node
        org = Organization(name=str(uuid.uuid1()))
        org.save()
        col = Collaboration(name=str(uuid.uuid1()), organizations=[org])
        col.save()
        node = Node(organization=org, collaboration=col)
        node.save()

        # try to view without permissions
        headers = self.get_user_auth_header(org)
        results, json_data = self.paginated_list(
            f"/api/node?organization_id={org.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view with organization permissions
        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/node?organization_id={org.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # try to view other organization
        headers = self.get_user_auth_header(rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/node?organization_id={org.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view with global permissions
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/node?organization_id={org.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # try to view as node
        headers = self.create_node_and_login(organization=org)
        results, json_data = self.paginated_list(
            f"/api/node?organization_id={org.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # try to view as node from another organization
        headers = self.create_node_and_login()
        results, json_data = self.paginated_list(
            f"/api/node?organization_id={org.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        node.delete()

    def test_organization_view_collaboration_permissions(self):
        # test unknown organization
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        headers = self.get_user_auth_header()

        # test that we can't view without permissions
        results, json_data = self.paginated_list(
            f"/api/collaboration?organization_id={org.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test view with organization scope
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/collaboration?organization_id={org.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test view with organization scope other organiation
        headers = self.get_user_auth_header(rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/collaboration?organization_id={org.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test view with global scope
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/collaboration?organization_id={org.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test as node
        headers = self.create_node_and_login(organization=org, collaboration=col)
        results, json_data = self.paginated_list(
            f"/api/collaboration?organization_id={org.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test as node other organization - should not be permitted
        results, json_data = self.paginated_list(
            f"/api/collaboration?organization_id={org.id + 1}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

    def test_view_collaboration_permissions(self):
        # setup organization and collaboration
        org = Organization()
        col = Collaboration(organizations=[org])
        col.save()

        # try view the collaboration without any permissions
        headers = self.get_user_auth_header(organization=org)
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view it with organization permissions
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # try to view it from an outside organization
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # view it with global view permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test access as node
        headers = self.create_node_and_login(organization=org, collaboration=col)
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test access as container
        headers = self.login_container(collaboration=col, organization=org)
        results = self.app.get(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        org.delete()
        col.delete()

    def test_edit_collaboration_permissions(self):
        # test an unknown collaboration
        headers = self.get_user_auth_header()
        results = self.app.patch("/api/collaboration/9999", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test editing without any permission
        col = Collaboration(name="collaboration-1")
        col.save()
        headers = self.get_user_auth_header()
        results = self.app.patch(
            f"/api/collaboration/{col.id}",
            headers=headers,
            json={"name": "this-aint-gonna-fly"},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test editing with global permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.patch(
            f"/api/collaboration/{col.id}",
            headers=headers,
            json={"name": "this-is-gonna-fly"},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "this-is-gonna-fly")
        col.delete()

        # test editing collaboration from within the collaboration
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()
        rule = Rule.get_by_(
            "collaboration", scope=Scope.COLLABORATION, operation=Operation.EDIT
        )
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.patch(
            f"/api/collaboration/{col.id}", headers=headers, json={"name": "some-name"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # check editing collaboration outside the collaboration fails without
        # root access
        org2 = Organization()
        org2.save()
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        results = self.app.patch(
            f"/api/collaboration/{col.id}",
            headers=headers,
            json={"name": "not-going-to-happen"},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        org.delete()
        org2.delete()
        col.delete()

    def test_delete_collaboration_permissions(self):
        col = Collaboration()
        col.save()

        # test deleting unknown collaboration
        headers = self.get_user_auth_header()
        results = self.app.delete("/api/collaboration/9999", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test deleting without permission
        results = self.app.delete(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test deleting with permission
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # check deleting with collaboration permission outside the
        # collaboration fails
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()
        org_not_member = Organization()
        org_not_member.save()
        rule = Rule.get_by_("collaboration", Scope.COLLABORATION, Operation.DELETE)
        headers = self.get_user_auth_header(organization=org_not_member, rules=[rule])
        result = self.app.delete(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # check deleting with collaboration permission inside the collaboration
        # succeeds
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        result = self.app.delete(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # ensure that collaboration exists again
        col = Collaboration()
        col.save()

        # test that collaboration cannot be deleted if it has resources inside it
        task = Task(collaboration=col)
        task.save()
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.delete(f"/api/collaboration/{col.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

        # but if defining the delete_dependents parameter it should work
        result = self.app.delete(
            f"/api/collaboration/{col.id}?delete_dependents=true", headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # cleanup
        org.delete()
        org_not_member.delete()

    def test_view_collaboration_organization_permissions_as_user(self):
        headers = self.get_user_auth_header()

        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        # access without the proper permissions
        headers = self.get_user_auth_header(organization=org)
        results, json_data = self.paginated_list(
            f"/api/organization?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # global permissions
        rule = Rule.get_by_("organization", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/organization?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # organization permissions of another organization
        rule = Rule.get_by_("organization", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/organization?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # now with the correct organization but without the correct permissions
        rule = Rule.get_by_("organization", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/organization?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # now with the correct organization and the correct permissions
        rule = Rule.get_by_("organization", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/organization?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(col.organizations))

    def test_view_collaboration_organization_permissions_as_node(self):
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        # node of a different organization
        headers = self.create_node_and_login()
        results, json_data = self.paginated_list(
            f"/api/organization?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # node of the correct organization
        headers = self.create_node_and_login(organization=org, collaboration=col)
        results, json_data = self.paginated_list(
            f"/api/organization?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(col.organizations))

    def test_view_collaboration_organization_permissions_as_container(self):
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        # container of a different organization
        headers = self.login_container()
        results, json_data = self.paginated_list(
            f"/api/organization?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # container of the correct organization
        headers = self.login_container(organization=org, collaboration=col)
        results, json_data = self.paginated_list(
            f"/api/organization?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(col.organizations))

    def test_edit_collaboration_organization_permissions(self):
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()

        org2 = Organization()
        org2.save()

        # try to do it without permission
        headers = self.get_user_auth_header()
        results = self.app.post(
            f"/api/collaboration/{col.id}/organization",
            headers=headers,
            json={"id": org2.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # edit permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post(
            f"/api/collaboration/{col.id}/organization",
            headers=headers,
            json={"id": org2.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json), 2)

        # test adding new organization to collaboration from within the
        # collaboration
        org3 = Organization()
        org3.save()
        rule = Rule.get_by_(
            "collaboration", scope=Scope.COLLABORATION, operation=Operation.EDIT
        )
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.post(
            f"/api/collaboration/{col.id}/organization",
            headers=headers,
            json={"id": org3.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # adding new organization to collaboration from outside the
        # collaboration should fail with collaboration permission
        org4 = Organization()
        org4.save()
        headers = self.get_user_auth_header(organization=org4, rules=[rule])
        results = self.app.post(
            f"/api/collaboration/{col.id}/organization",
            headers=headers,
            json={"id": org4.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        org4.delete()
        col.delete()

    def test_delete_collaboration_organization_permissions(self):
        org = Organization()
        org.save()
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()

        # try to do it without permission
        headers = self.get_user_auth_header()
        results = self.app.delete(
            f"/api/collaboration/{col.id}/organization",
            headers=headers,
            json={"id": org.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # delete first organization
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(
            f"/api/collaboration/{col.id}/organization",
            headers=headers,
            json={"id": org.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json), 1)  # one organization left

        # add back first organization
        col.organizations.append(org)
        col.save()

        # removing organization from collaboration from outside the
        # collaboration should fail with collaboration permission
        org3 = Organization()
        org3.save()
        rule = Rule.get_by_(
            "collaboration", scope=Scope.COLLABORATION, operation=Operation.EDIT
        )
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        results = self.app.delete(
            f"/api/collaboration/{col.id}/organization",
            headers=headers,
            json={"id": org2.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test removing organization from collaboration from within the
        # collaboration
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.delete(
            f"/api/collaboration/{col.id}/organization",
            headers=headers,
            json={"id": org2.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()

    def test_view_collaboration_node_permissions(self):
        org = Organization(name=str(uuid.uuid1()))
        col = Collaboration(name=str(uuid.uuid1()), organizations=[org])
        node = Node(collaboration=col, organization=org)
        node.save()

        # try to view without any permissions
        headers = self.get_user_auth_header()
        results, json_data = self.paginated_list(
            "/api/node?collaboration_id=9999", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view from another organzization
        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/node?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(len(json_data), 0)

        # try to view from another organization with global permissions
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/node?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(col.nodes))

        # try to view your collaboration's nodes with organization permissions
        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule], organization=org)
        results, json_data = self.paginated_list(
            f"/api/node?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # and now with collaboration permissions
        rule = Rule.get_by_("node", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule], organization=org)
        results, json_data = self.paginated_list(
            f"/api/node?collaboration_id={col.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(col.nodes))

        # cleanup
        node.delete()

    def test_add_collaboration_node_permissions(self):
        org = Organization()
        org.save()
        org2 = Organization()
        org2.save()
        col = Collaboration(organizations=[org, org2])
        col.save()
        node = Node(organization=org)
        node.save()
        node2 = Node(organization=org2)
        node2.save()

        org3 = Organization()
        org3.save()
        node3 = Node(organization=org3)
        node3.save()

        # try non-existant collaboration
        headers = self.get_user_auth_header()

        results = self.app.post(
            "/api/collaboration/9999/node", headers=headers, json={"id": node.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # try without proper permissions
        results = self.app.post(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": node.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to add non-existing node
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": 9999}
        )
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # add a node!
        results = self.app.post(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": node.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.CREATED)
        self.assertEqual(len(results.json), len(col.nodes))

        # try to add a node thats already in there
        results = self.app.post(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": node.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # adding new node to collaboration from an organization that is not
        # part of the collaboration should fail
        results = self.app.post(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": node3.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # test new node to collaboration from within the collaboration
        rule = Rule.get_by_(
            "collaboration", scope=Scope.COLLABORATION, operation=Operation.EDIT
        )
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.post(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": node2.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # adding new node to collaboration from outside collaboration should
        # fail with collaboration-scope permission
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        results = self.app.post(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": node3.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        node.delete()
        node2.delete()
        node3.delete()
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()

    def test_delete_collaboration_node_permissions(self):
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        node = Node(organization=org, collaboration=col)
        node.save()

        # try non-existant collaboration
        headers = self.get_user_auth_header()
        results = self.app.delete(
            "/api/collaboration/9999/node", headers=headers, json={"id": node.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # try without proper permissions
        results = self.app.delete(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": node.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to add non-existing node
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": 9999}
        )
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # try to add a node thats not in there
        node2 = Node()
        node2.save()
        results = self.app.delete(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": node2.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)
        node2.delete()

        # delete node from collaboration!
        results = self.app.delete(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": node.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # removing node from collaboration from outside the
        # collaboration should fail with collaboration permission
        node2 = Node(organization=org2, collaboration=col)
        node2.save()
        org3 = Organization()
        org3.save()
        rule = Rule.get_by_(
            "collaboration", scope=Scope.COLLABORATION, operation=Operation.EDIT
        )
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        results = self.app.delete(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": node2.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test removing organization from collaboration from within the
        # collaboration
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.delete(
            f"/api/collaboration/{col.id}/node", headers=headers, json={"id": node2.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        node.delete()
        node2.delete()
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()

    def test_view_node_permissions_as_user(self):
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        node = Node(organization=org, collaboration=col)
        node.save()
        node2 = Node(organization=org2, collaboration=col)
        node2.save()

        # view non existing node
        headers = self.get_user_auth_header()
        results = self.app.get("/api/node/9999", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # missing permissions
        results = self.app.get(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # organization permissions
        rule1 = Rule.get_by_("node", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule1])
        results = self.app.get(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # organization permissions from another organization
        headers = self.get_user_auth_header(rules=[rule1])
        results = self.app.get(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # global permissions
        rule2 = Rule.get_by_("node", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule2])
        results = self.app.get(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # list organization permissions
        headers = self.get_user_auth_header(organization=org, rules=[rule1])
        results = self.app.get("/api/node", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), 1)  # collab has 1 node

        # list global permissions
        headers = self.get_user_auth_header(rules=[rule2])
        results, json_data = self.paginated_list("/api/node", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(Node.get()))

        # collaboration permission inside the collaboration
        rule = Rule.get_by_("node", scope=Scope.COLLABORATION, operation=Operation.VIEW)
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        results = self.app.get(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # list collaboration permissions - in collaboration
        results = self.app.get("/api/node", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), len(col.nodes))

        # collaboration permission outside the collaboration should fail
        org3 = Organization()
        org3.save()
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        results = self.app.get(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # list collaboration permissions - other collaboration
        results = self.app.get(
            "/api/node", headers=headers, query_string={"collaboration_id": col.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        node.delete()
        node2.delete()
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()

    def test_view_node_permissions_as_node(self):
        org = Organization()
        col = Collaboration(organizations=[org])
        node, api_key = self.create_node(org, col)

        headers = self.login_node(api_key)

        # global permissions
        results = self.app.get(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # list organization permissions
        results = self.app.get("/api/node", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), len(org.nodes))

        # cleanup
        node.delete()

    def test_create_node_permissions(self):
        org = Organization(name=str(uuid.uuid1()))
        col = Collaboration(organizations=[org])
        col.save()
        org2 = Organization(name=str(uuid.uuid1()))
        org2.save()

        # test non existing collaboration
        headers = self.get_user_auth_header()
        results = self.app.post(
            "/api/node", headers=headers, json={"collaboration_id": 9999}
        )
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test creating a node without any permissions
        headers = self.get_user_auth_header()
        results = self.app.post(
            "/api/node", headers=headers, json={"collaboration_id": col.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # testing creating a node with organization permissions and supplying
        # an organization id
        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.CREATE)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.post(
            "/api/node",
            headers=headers,
            json={"collaboration_id": col.id, "organization_id": org.id},
        )

        self.assertEqual(results.status_code, HTTPStatus.CREATED)
        node_id = results.json.get("id")
        results = self.app.post(
            "/api/node",
            headers=headers,
            json={"collaboration_id": col.id, "organization_id": org2.id},  # <-------
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test adding a node to an collaboration from an organization which
        # does not belong to the collaboration
        rule2 = Rule.get_by_("node", Scope.GLOBAL, Operation.CREATE)
        headers = self.get_user_auth_header(organization=org2, rules=[rule2])
        results = self.app.post(
            "/api/node", headers=headers, json={"collaboration_id": col.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # check an creating an already existing node
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.post(
            "/api/node", headers=headers, json={"collaboration_id": col.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # lets retry that
        node = Node.get(node_id)
        node.delete()
        results = self.app.post(
            "/api/node", headers=headers, json={"collaboration_id": col.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # test global permissions
        col.organizations.append(org2)
        col.save()
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.CREATE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post(
            "/api/node",
            headers=headers,
            json={"collaboration_id": col.id, "organization_id": org2.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # test collaboration permissions
        org3 = Organization()
        org3.save()
        col.organizations.append(org3)
        col.save()
        rule = Rule.get_by_(
            "node", scope=Scope.COLLABORATION, operation=Operation.CREATE
        )
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        result = self.app.post(
            "/api/node",
            headers=headers,
            json={"collaboration_id": col.id, "organization_id": org3.id},
        )
        self.assertEqual(result.status_code, HTTPStatus.CREATED)

        # test collaboration permissions - outside of collaboration should fail
        org4 = Organization()
        org4.save()
        col.organizations.append(org4)
        col.save()
        headers = self.get_user_auth_header(organization=Organization(), rules=[rule])
        result = self.app.post(
            "/api/node",
            headers=headers,
            json={"collaboration_id": col.id, "organization_id": org4.id},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        org4.delete()
        col.delete()
        # delete the last three nodes (i.e. those that were created in this test)
        for resource in Node.get()[::-1][:3]:
            resource.delete()

    def test_delete_node_permissions(self):
        org = Organization(name=str(uuid.uuid1()))
        col = Collaboration(name=str(uuid.uuid1()), organizations=[org])
        node = Node(organization=org, collaboration=col)
        node.save()

        # unexisting node
        headers = self.get_user_auth_header()
        results = self.app.delete("/api/node/9999", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # organization permission other organization
        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # organization permission
        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.DELETE)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.delete(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # global permission
        org2 = Organization(name=str(uuid.uuid1()))
        node2 = Node(organization=org2, collaboration=col)
        node2.save()
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(f"/api/node/{node2.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # collaboration permission - removing node from outside collaboration
        # should fail
        org3 = Organization()
        node3 = Node(organization=org3, collaboration=col)
        node3.save()
        col.organizations.append(org3)
        col.save()
        org_not_in_collab = Organization()
        org_not_in_collab.save()
        rule = Rule.get_by_(
            "node", scope=Scope.COLLABORATION, operation=Operation.DELETE
        )
        headers = self.get_user_auth_header(
            organization=org_not_in_collab, rules=[rule]
        )
        results = self.app.delete(f"/api/node/{node3.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # collaboration permission - now within collaboration
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.delete(f"/api/node/{node3.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        org_not_in_collab.delete()
        col.delete()

    def test_patch_node_permissions_as_user(self):
        # test patching non-existant node
        headers = self.get_user_auth_header()
        results = self.app.patch("/api/node/9999", headers=headers, json={})
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test user without any permissions
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        node = Node(organization=org, collaboration=col)
        node.save()

        results = self.app.patch(f"/api/node/{node.id}", headers=headers, json={})
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test user with global permissions
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.patch(
            f"/api/node/{node.id}", headers=headers, json={"name": "A"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "A")

        # test user with org permissions and own organization
        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.EDIT)
        headers = self.get_user_auth_header(org, [rule])
        results = self.app.patch(
            f"/api/node/{node.id}", headers=headers, json={"name": "B"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "B")

        # test user with org permissions and other organization
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.patch(
            f"/api/node/{node.id}", headers=headers, json={"name": "C"}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test updating the `organization_id` (which is not allowed)
        results = self.app.patch(
            f"/api/node/{node.id}", headers=headers, json={"organization_id": org2.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # test updating the collaboration_id (which is not allowed)
        results = self.app.patch(
            f"/api/node/{node.id}", headers=headers, json={"collaboration_id": col.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # try to patch the node's VPN IP address
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(org2, rules=[rule])
        results = self.app.patch(
            f"/api/node/{node.id}", headers=headers, json={"ip": "0.0.0.0"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["ip"], "0.0.0.0")

        # try to clear the node's VPN IP address - this should work
        results = self.app.patch(
            f"/api/node/{node.id}", headers=headers, json={"clear_ip": True}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["ip"], None)

        # collaboration permission - inside the collaboration
        rule = Rule.get_by_("node", Scope.COLLABORATION, Operation.EDIT)
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        results = self.app.patch(
            f"/api/node/{node.id}", headers=headers, json={"name": "A"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # collaboration permission - outside the collaboration
        org3 = Organization()
        org3.save()
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        results = self.app.patch(
            f"/api/node/{node.id}", headers=headers, json={"name": "A"}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        node.delete()
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()

    def test_view_task_permissions_as_user(self):
        # non existing task
        headers = self.get_user_auth_header()
        results = self.app.get("/api/task/9999", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test user without any permissions and id
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        task = Task(name="unit", collaboration=col, init_org=org)
        task.save()

        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test user with col permissions with id
        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "unit")

        # collaboration permission outside the collaboration should fail
        org_not_in_collab = Organization()
        org_not_in_collab.save()
        headers = self.get_user_auth_header(
            organization=org_not_in_collab, rules=[rule]
        )
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test user with org permissions with id from another org
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test user with org permissions without id
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test that user is not allowed to view task results without id
        results = self.app.get(
            "/api/task", headers=headers, query_string={"include": "results"}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test that user is allowed to view task results if they have the rule
        # to view results
        rule_view_results = Rule.get_by_("run", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule, rule_view_results])
        results = self.app.get(
            "/api/task", headers=headers, query_string={"include": "results"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test user with global permissions and id
        rule = Rule.get_by_("task", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test that user is not allowed to view task results with id
        results = self.app.get(
            f"/api/task/{task.id}", headers=headers, query_string={"include": "results"}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test that user is allowed to view task results if they have the rule
        # to view results
        headers = self.get_user_auth_header(org, rules=[rule, rule_view_results])
        results = self.app.get(
            f"/api/task/{task.id}", headers=headers, query_string={"include": "results"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test user with global permissions without id
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # list collaboration permissions - in collaboration
        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), len(col.tasks))

        # list collaboration permissions - other collaboration
        headers = self.get_user_auth_header(org_not_in_collab, rules=[rule])
        results = self.app.get(
            "/api/task", headers=headers, query_string={"collaboration_id": col.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # list own organization permissions - same organization
        rule = Rule.get_by_("task", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), len(col.tasks))

        # list own organization permissions - other organization
        headers = self.get_user_auth_header(org2, rules=[rule])
        results = self.app.get(
            "/api/task", headers=headers, query_string={"init_org_id": org.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # list own user's task permissions - same user without id
        rule = Rule.get_by_("task", Scope.OWN, Operation.VIEW)
        user = self.create_user(rules=[rule], organization=org)
        headers = self.login(user.username)
        task2 = Task(name="unit", collaboration=col, init_org=org, init_user=user)
        task2.save()
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), 1)

        # list own user's task permissions - same user with id
        results = self.app.get(f"/api/task/{task2.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # list own user's task permissions - other user without id
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.get(
            "/api/task", headers=headers, query_string={"init_user_id": user.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # list own user's task permissions - other user with id
        results = self.app.get(f"/api/task/{task2.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        task.delete()
        task2.delete()
        user.delete()
        org.delete()
        org2.delete()
        col.delete()

    def test_view_task_permissions_as_node_and_container(self):
        # test node with id
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()
        task = Task(collaboration=col, image="some-image", init_org=org)
        task.save()
        res = Run(task=task, status=RunStatus.PENDING)
        res.save()

        headers = self.create_node_and_login(organization=org)
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test node without id
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test container with id
        headers = self.login_container(collaboration=col, organization=org, task=task)
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test container without id
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    def test_create_task_permission_as_user(self):
        user = self.create_user()
        headers = self.login(user.username)

        input_ = bytes_to_base64s(serialize({"method": "dummy"}))

        org = Organization()
        org.save()
        col = Collaboration(organizations=[org], encrypted=False)
        col.save()
        session = Session(name="test_session", user_id=user.id, collaboration=col)
        session.save()

        # test non-existing collaboration
        task_json = {
            "collaboration_id": 9999,
            "organizations": [{"id": 9999, "input": input_}],
            "image": "some-image",
            "session_id": session.id,
        }
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # task without any node created
        task_json["organizations"] = [{"id": org.id, "input": input_}]
        task_json["collaboration_id"] = col.id
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # node is used implicitly as in further checks, can only create task
        # if node has been created
        node = Node(organization=org, collaboration=col)
        node.save()
        org2 = Organization()
        org2.save()

        # test user outside the collaboration
        task_json["organizations"] = [{"id": org2.id, "input": input_}]
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # user in the collaboration but still without any permissions
        task_json["organizations"] = [{"id": org.id, "input": input_}]
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # user with organization permissions for other organization
        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.CREATE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # user with organization permissions
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # user with global permissions but outside of the collaboration. They
        # should *not* be allowed to create a task in a collaboration that
        # they're not a part of
        # TODO add test for user with global permission that creates a task for
        # another organization than their own in the same collaboration
        rule = Rule.get_by_("task", Scope.GLOBAL, Operation.CREATE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # check that no tasks can be created with organizations outside a study but
        # within the collaboration
        col2 = Collaboration(organizations=[org, org2])
        col2.save()
        study = Study(organizations=[org], collaboration=col2)
        study.save()
        task_json["collaboration_id"] = col2.id
        task_json["organizations"] = [{"id": org2.id, "input": input_}]
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # cleanup
        # delete the 1 task that was created in this unit test
        Task.get()[::-1][0].delete()
        session.delete()
        node.delete()
        org.delete()
        org2.delete()
        col.delete()
        col2.delete()
        study.delete()

    def test_create_task_permissions_as_container(self):
        org = Organization()
        col = Collaboration(organizations=[org], encrypted=False)

        user = self.create_user()
        headers = self.login()

        session = Session(name="test_session", user_id=user.id, collaboration=col)
        session.save()

        parent_task = Task(collaboration=col, image="some-image")
        parent_task.save()
        parent_res = Run(organization=org, task=parent_task, status=RunStatus.PENDING)
        parent_res.save()

        input_ = bytes_to_base64s(serialize({"method": "dummy"}))
        headers = self.login_container(
            collaboration=col, organization=org, task=parent_task
        )

        # test other collaboration_id
        col2 = Collaboration(organizations=[org])
        col2.save()
        node2 = Node(organization=org, collaboration=col2)
        node2.save()
        results = self.app.post(
            "/api/task",
            headers=headers,
            json={
                "organizations": [{"id": org.id, "input": input_}],
                "collaboration_id": col2.id,
                "image": "some-image",
                "session_id": session.id,
            },
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test with correct parameters
        results = self.app.post(
            "/api/task",
            headers=headers,
            json={
                "organizations": [{"id": org.id, "input": input_}],
                "collaboration_id": col.id,
                "image": "some-image",
                "session_id": session.id,
            },
        )
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # test already completed task
        parent_res.status = RunStatus.COMPLETED
        parent_res.save()
        results = self.app.post(
            "/api/task",
            headers=headers,
            json={
                "organizations": [{"id": org.id, "input": input_}],
                "collaboration_id": col.id,
                "image": "some-image",
                "session_id": session.id,
            },
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test a failed task
        parent_res.status = RunStatus.FAILED
        parent_res.save()
        results = self.app.post(
            "/api/task",
            headers=headers,
            json={
                "organizations": [{"id": org.id, "input": input_}],
                "collaboration_id": col.id,
                "image": "some-image",
                "session_id": session.id,
            },
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        Task.get()[::-1][0].delete()
        session.delete()
        org.delete()
        col.delete()
        node2.delete()
        col2.delete()
        # delete the 1 task that was created in this unit test

    def test_delete_task_permissions(self):
        # test non-existing task
        headers = self.get_user_auth_header()
        self.app.delete("/api/task/9999", headers=headers)

        # test with organization permissions from other organization
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        task = Task(collaboration=col, init_org=org)
        task.save()

        # test with user who is not member of collaboration
        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test with collaboration permissions
        headers = self.get_user_auth_header(org, [rule])
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test with global permissions
        task = Task(collaboration=col)
        task.save()
        rule = Rule.get_by_("task", Scope.GLOBAL, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test that all results are also deleted
        task = Task(collaboration=col)
        run = Run(task=task)
        run.save()
        run_id = run.id  # cannot access this after deletion
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertIsNone(Task.get(run_id))

        # test permission to delete tasks of own organization - other
        # organization should fail
        task = Task(collaboration=col, init_org=org)
        task.save()
        rule = Rule.get_by_("task", Scope.ORGANIZATION, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule], organization=org2)
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test permission to delete tasks of own organization - should work
        headers = self.get_user_auth_header(rules=[rule], organization=org)
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test permission to delete own tasks - other user of organization
        # should fail
        rule = Rule.get_by_("task", Scope.OWN, Operation.DELETE)
        user = self.create_user(rules=[rule], organization=org)
        task = Task(collaboration=col, init_org=org, init_user=user)
        task.save()
        headers = self.get_user_auth_header(rules=[rule], organization=org)
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test permission to delete own tasks with same user
        headers = self.login(user.username)
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        user.delete()
        org.delete()
        org2.delete()
        col.delete()

    def test_view_task_result_permissions_as_user(self):
        # non-existing task
        headers = self.get_user_auth_header()
        result = self.app.get("/api/task/9999/run", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # test with organization permissions from other organization
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        col.save()
        task = Task(collaboration=col, init_org=org)
        task.save()
        # NB: node is used implicitly in task/{id}/result schema
        node = Node(organization=org, collaboration=col)
        node.save()
        res = Run(task=task, organization=org)
        res.save()

        # Test with permissions of someone who is not in the collaboration
        rule = Rule.get_by_("run", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test with collaboration permission
        headers = self.get_user_auth_header(org, [rule])
        result = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test with global permission
        rule = Rule.get_by_("run", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test also result endpoint
        rule = Rule.get_by_("run", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.get(f"/api/result?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test result endpoint with organization permission
        headers = self.get_user_auth_header(org, [rule])
        result = self.app.get(f"/api/result?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test result endpoint with global permission
        rule = Rule.get_by_("run", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.get(f"/api/result?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test with organization permission
        rule = Rule.get_by_("run", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, [rule])
        result = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        result = self.app.get(f"/api/run/{res.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test with organization permission - other organization should fail
        headers = self.get_user_auth_header(org2, [rule])
        result = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        result = self.app.get(f"/api/run/{res.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test with permission to view own runs
        rule = Rule.get_by_("run", Scope.OWN, Operation.VIEW)
        user = self.create_user(rules=[rule], organization=org)
        headers = self.login(user.username)
        task2 = Task(collaboration=col, init_org=org, init_user=user)
        task2.save()
        res2 = Run(task=task2, organization=org)
        res2.save()
        result = self.app.get(f"/api/run?task_id={task2.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        result = self.app.get(f"/api/run/{res2.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test with permission to view own runs - other user should fail
        headers = self.get_user_auth_header(rules=[rule], organization=org)
        result = self.app.get(f"/api/run?task_id={task2.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        result = self.app.get(f"/api/run/{res2.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        node.delete()
        task.delete()
        task2.delete()
        res.delete()
        res2.delete()
        org.delete()
        org2.delete()
        col.delete()

    def test_view_task_run_permissions_as_container(self):
        # test if container can
        org = Organization()
        col = Collaboration(organizations=[org])
        task = Task(collaboration=col, image="some-image", init_org=org)
        task.save()
        res = Run(task=task, organization=org, status=RunStatus.PENDING)
        res.save()

        headers = self.login_container(collaboration=col, organization=org, task=task)
        results = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    @patch(
        "vantage6.server.algo_store_communication.request_algo_store",
        return_value=("success", HTTPStatus.CREATED),
    )
    def test_create_algorithm_store_record(self, _request_algo_store):
        """Test creating an algorithm store record"""
        # initialize resources
        org = Organization()
        col = Collaboration(organizations=[org])
        col.save()
        headers = self.get_user_auth_header(organization=org)

        record = {
            "name": "test",
            "algorithm_store_url": "http://test.com",
            "server_url": "http://test2.com",
            "collaboration_id": col.id,
        }

        # test creating a record without any permissions
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test creating a record with collaboration permissions if not member
        # of the collaboration
        rule = Rule.get_by_("collaboration", Scope.COLLABORATION, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test creating a record with collaboration permissions if member
        # of the collaboration
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # test that doing it again fails because the record already exists
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # test that we cannot create a record for all collaborations with
        # collaboration permissions
        del record["collaboration_id"]
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test creating a record with global permissions. Note that while we
        # are creating the same algorithm store record, we are doing it for
        # all collaborations, so it should succeed
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # test that creating a record for a localhost algorithm store fails
        record["algorithm_store_url"] = "http://localhost:5000"
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)
        record["algorithm_store_url"] = "http://127.0.0.1:5000"
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # by using force we should be able to create a record for a localhost
        # algorithm store
        record["force"] = True
        results = self.app.post("/api/algorithmstore", headers=headers, json=record)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # cleanup
        org.delete()
        col.delete()
        for resource in AlgorithmStore.get():
            resource.delete()

    def test_view_algorithm_store(self):
        """Test viewing algorithm store records"""
        # without permissions
        headers = self.get_user_auth_header()
        results = self.app.get("/api/algorithmstore", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # view with organization permissions
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        col.save()
        algo_store = AlgorithmStore(
            name="test", url="http://test.com", collaboration=col
        )
        algo_store.save()
        rule = Rule.get_by_("collaboration", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule])

        # list. We expect to find all stores without specified collaboration and this one
        results = self.app.get("/api/algorithmstore", headers=headers)
        all_stores = AlgorithmStore.get()
        num_stores_to_find = (
            len([store for store in all_stores if store.collaboration_id is None]) + 1
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), num_stores_to_find)
        # single record
        results = self.app.get(f"/api/algorithmstore/{algo_store.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # view with another organization within the same collaboration
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        results = self.app.get(
            "/api/algorithmstore",
            headers=headers,
            query_string={"collaboration_id": col.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), num_stores_to_find)
        results = self.app.get(f"/api/algorithmstore/{algo_store.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # try to view with organization permissions but not member of
        # collaboration
        org3 = Organization()
        org3.save()
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        results = self.app.get(f"/api/algorithmstore/{algo_store.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # view with global permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.get("/api/algorithmstore", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), len(AlgorithmStore.get()))

        results = self.app.get(f"/api/algorithmstore/{algo_store.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()
        algo_store.delete()

    def test_patch_algorithm_store(self):
        """Test patching algorithm store records"""
        # initialize resources
        org = Organization()
        col = Collaboration(organizations=[org])
        col.save()
        algo_store = AlgorithmStore(
            name="test", url="http://test.com", collaboration=col
        )
        algo_store.save()

        # test patching without any permissions
        headers = self.get_user_auth_header()
        results = self.app.patch(
            f"/api/algorithmstore/{algo_store.id}",
            headers=headers,
            json={"name": "test1"},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test patching non-existing record
        rule = Rule.get_by_("collaboration", Scope.COLLABORATION, Operation.EDIT)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.patch("/api/algorithmstore/9999", headers=headers, json={})
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test patching with collaboration permissions
        results = self.app.patch(
            f"/api/algorithmstore/{algo_store.id}",
            headers=headers,
            json={"name": "test2"},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "test2")

        # test patching with global permissions
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.patch(
            f"/api/algorithmstore/{algo_store.id}",
            headers=headers,
            json={"name": "test3"},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "test3")

        # cleanup
        org.delete()
        col.delete()
        algo_store.delete()

    @patch(
        "vantage6.server.resource.algorithm_store.request_algo_store",
    )
    def test_delete_algorithm_store(self, request_algo_store):
        """Test deleting algorithm store records"""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"id": "1"}]
        request_algo_store.return_value = (mock_response, HTTPStatus.OK)

        # initialize resources
        org = Organization()
        col = Collaboration(organizations=[org])
        col.save()
        algo_store = AlgorithmStore(
            name="test",
            url="http://test.com",
            collaboration_id=col.id,
        )
        algo_store.save()
        params = {"server_url": "http://test.com"}

        # test deleting without any permissions
        headers = self.get_user_auth_header()
        results = self.app.delete(
            f"/api/algorithmstore/{algo_store.id}", headers=headers, query_string=params
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test deleting non-existing record
        rule = Rule.get_by_("collaboration", Scope.COLLABORATION, Operation.EDIT)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.delete(
            "/api/algorithmstore/9999", headers=headers, query_string=params
        )
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test deleting with collaboration permissions
        results = self.app.delete(
            f"/api/algorithmstore/{algo_store.id}", headers=headers, query_string=params
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test deleting with global permissions
        algo_store = AlgorithmStore(
            name="test2",
            url="http://test.com",
            collaboration_id=col.id,
        )
        algo_store.save()
        rule = Rule.get_by_("collaboration", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(
            f"/api/algorithmstore/{algo_store.id}", headers=headers, query_string=params
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        org.delete()
        col.delete()

    def test_view_study_permissions(self):
        # setup organization and collaboration
        org = Organization()
        org2 = Organization()
        org_outside_collab = Organization()
        col = Collaboration(organizations=[org, org2])
        other_col = Collaboration(organizations=[org_outside_collab])
        study = Study(collaboration=col, organizations=[org])
        study2 = Study(collaboration=col, organizations=[org2])
        study.save()
        study2.save()
        other_study = Study(collaboration=other_col, organizations=[org_outside_collab])
        other_study.save()

        # try view the study without any permissions
        headers = self.get_user_auth_header(organization=org)
        results = self.app.get("/api/study", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view it with organization permissions - should give one of two studies
        rule = Rule.get_by_("study", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.get("/api/study", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), 1)

        # try to view with collaboration permission - should give both studies within
        # the collaboration but not the other one
        rule = Rule.get_by_("study", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.get("/api/study", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), 2)

        # with global permissions, should get all three
        rule = Rule.get_by_("study", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.get("/api/study", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), len(Study.get()))

        # -----  Now for the endpoint with ID --------

        # try view the study without any permissions
        headers = self.get_user_auth_header(organization=org)
        results = self.app.get(f"/api/study/{study.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view it with organization permissions
        rule = Rule.get_by_("study", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.get(f"/api/study/{study.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # try to view it with organization permissions from another organization that
        # is member of collaboration but not of the study (should not be allowed)
        results = self.app.get(f"/api/study/{study2.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view it with collaboration permissions from another organization that
        # is member of collaboration but not of the study (should be allowed)
        rule = Rule.get_by_("study", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.get(f"/api/study/{study2.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # view it with global view permissions outside of collaboration
        rule = Rule.get_by_("study", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.get(f"/api/study/{study.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test access as node
        headers = self.create_node_and_login(organization=org, collaboration=col)
        results = self.app.get(f"/api/study/{study.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test access as node of study that organization is not a part of
        headers = self.create_node_and_login(organization=org, collaboration=col)
        results = self.app.get(f"/api/study/{study2.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test access as container
        headers = self.login_container(collaboration=col, organization=org)
        results = self.app.get(f"/api/study/{study.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test access as container of study that organization is not a part of
        headers = self.login_container(collaboration=col, organization=org)
        results = self.app.get(f"/api/study/{study2.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        org.delete()
        org2.delete()
        col.delete()
        study.delete()
        study2.delete()
        org_outside_collab.delete()
        other_col.delete()
        other_study.delete()

    def test_edit_study_permissions(self):
        # test an unknown study
        headers = self.get_user_auth_header()
        results = self.app.patch("/api/study/9999", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        study = Study(collaboration=col, organizations=[org], name="study-3")
        study2 = Study(collaboration=col, organizations=[org2])
        study.save()
        study2.save()

        # test editing without any permission
        headers = self.get_user_auth_header()
        results = self.app.patch(
            f"/api/study/{study.id}",
            headers=headers,
            json={"name": "this-aint-gonna-fly"},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test editing with global permissions
        rule = Rule.get_by_("study", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.patch(
            f"/api/study/{study.id}",
            headers=headers,
            json={"name": "this-is-gonna-fly"},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "this-is-gonna-fly")

        # test editing study from within the study
        rule = Rule.get_by_("study", scope=Scope.ORGANIZATION, operation=Operation.EDIT)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.patch(
            f"/api/study/{study.id}", headers=headers, json={"name": "unique-name"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test editing study from organization not part of the study (but part of the
        # collaboration)
        results = self.app.patch(
            f"/api/study/{study2.id}", headers=headers, json={"name": "other-uniq-name"}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # check that this IS possible when you have collaboration permissions
        rule = Rule.get_by_(
            "study", scope=Scope.COLLABORATION, operation=Operation.EDIT
        )
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.patch(
            f"/api/study/{study2.id}", headers=headers, json={"name": "other-uniq-name"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # check editing collaboration outside the collaboration fails without
        # root access
        org3 = Organization()
        org3.save()
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        results = self.app.patch(
            f"/api/study/{study.id}",
            headers=headers,
            json={"name": "not-going-to-happen"},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test that with root access it works
        rule = Rule.get_by_("study", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.patch(
            f"/api/study/{study.id}",
            headers=headers,
            json={"name": "this-is-gonna-fly-2"},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        col.delete()
        study.delete()
        study2.delete()

    def test_delete_study_permissions(self):
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        study = Study(collaboration=col, organizations=[org], name="study-1")
        study2 = Study(collaboration=col, organizations=[org2])
        study.save()
        study2.save()

        # test deleting non-existing study
        headers = self.get_user_auth_header()
        results = self.app.delete("/api/study/9999", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test deleting without permission
        results = self.app.delete(f"/api/study/{study.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test deleting with organization permission fails outside of the study
        rule = Rule.get_by_("study", Scope.ORGANIZATION, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule], organization=org)
        results = self.app.delete(f"/api/study/{study2.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test that organization permission does work if organization is part of the
        # study
        results = self.app.delete(f"/api/study/{study.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # check deleting with collaboration permission outside the
        # collaboration fails
        rule = Rule.get_by_("study", Scope.COLLABORATION, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.delete(f"/api/study/{study2.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # check that it does work within the collaboration
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        result = self.app.delete(f"/api/study/{study2.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # create new study as both have been deleted
        study = Study(collaboration=col, organizations=[org], name="study-1")
        study.save()

        # check deleting with global permission succeeds
        rule = Rule.get_by_("study", Scope.GLOBAL, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.delete(f"/api/study/{study.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # cleanup
        org.delete()
        org2.delete()
        col.delete()

    def test_create_study_permissions(self):
        org = Organization()
        org2 = Organization()
        org_not_in_collab = Organization()
        col = Collaboration(organizations=[org, org2])
        col.save()

        # test with wrong request body
        headers = self.get_user_auth_header(organization=org)
        results = self.app.post(
            "/api/study", headers=headers, json={"wrong-key": "test"}
        )
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # test without organizations - should not work
        json_data = {"collaboration_id": col.id, "name": "some-name"}
        results = self.app.post("/api/study", headers=headers, json=json_data)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # test without permissions
        json_data["organization_ids"] = [org.id]
        results = self.app.post("/api/study", headers=headers, json=json_data)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test with collaboration permissions
        rule = Rule.get_by_("study", Scope.COLLABORATION, Operation.CREATE)
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.post("/api/study", headers=headers, json=json_data)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # test with collaboration permissions from outside collaboration
        json_data["name"] = "some-other-unique-name"
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post("/api/study", headers=headers, json=json_data)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test with global permissions
        rule = Rule.get_by_("study", Scope.GLOBAL, Operation.CREATE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post("/api/study", headers=headers, json=json_data)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # check that doesnt work with orgs outside collab
        json_data["name"] = "again-another-name"
        json_data["organization_ids"] = [org_not_in_collab.id]
        results = self.app.post("/api/study", headers=headers, json=json_data)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # cleanup
        org.delete()
        org2.delete()
        col.delete()
        for resource in Study.get():
            resource.delete()

    def test_view_study_organization_permissions_as_user(self):
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        col.save()
        study = Study(collaboration=col, organizations=[org])
        study.save()

        # access without the proper permissions
        headers = self.get_user_auth_header(organization=org)
        results, json_data = self.paginated_list(
            f"/api/organization?study_id={study.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # global permissions
        rule = Rule.get_by_("organization", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/organization?study_id={study.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # collaboration permissions outside of collaboration
        rule = Rule.get_by_("organization", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/organization?study_id={study.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # now inside the collaboration
        headers = self.get_user_auth_header(organization=org2, rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/organization?study_id={study.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(study.organizations))

        # cleanup
        org.delete()
        org2.delete()
        col.delete()
        study.delete()

    def test_view_study_organization_permissions_as_node(self):
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        study = Study(collaboration=col, organizations=[org])
        study.save()

        # node of a different organization but not within the collaboration
        headers = self.create_node_and_login()
        results, json_data = self.paginated_list(
            f"/api/organization?study_id={study.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # node of the correct organization
        headers = self.create_node_and_login(organization=org, collaboration=col)
        results, json_data = self.paginated_list(
            f"/api/organization?study_id={study.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(study.organizations))

        # cleanup
        org.delete()
        org2.delete()
        col.delete()
        study.delete()

    def test_view_study_organization_permissions_as_container(self):
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        study = Study(collaboration=col, organizations=[org])
        study.save()

        # container of a different organization but not within the collaboration
        headers = self.login_container()
        results, json_data = self.paginated_list(
            f"/api/organization?study_id={study.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # container of the correct organization
        headers = self.login_container(organization=org, collaboration=col)
        results, json_data = self.paginated_list(
            f"/api/organization?study_id={study.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(study.organizations))

        # cleanup
        org.delete()
        org2.delete()
        col.delete()
        study.delete()

    def test_edit_study_organization_permissions(self):
        org = Organization()
        org2 = Organization()
        org3 = Organization()
        org_outside_collab = Organization()
        col = Collaboration(organizations=[org, org2, org3])
        study = Study(collaboration=col, organizations=[org])
        study.save()
        org_outside_collab.save()

        # try to add org2 without permission
        headers = self.get_user_auth_header()
        results = self.app.post(
            f"/api/study/{study.id}/organization",
            headers=headers,
            json={"id": org2.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test adding new organization to study from within the collaboration
        rule = Rule.get_by_(
            "study", scope=Scope.COLLABORATION, operation=Operation.EDIT
        )
        headers = self.get_user_auth_header(organization=org, rules=[rule])
        results = self.app.post(
            f"/api/study/{study.id}/organization",
            headers=headers,
            json={"id": org2.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # adding new organization to study from outside the
        # collaboration should fail with collaboration permission
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post(
            f"/api/study/{study.id}/organization",
            headers=headers,
            json={"id": org3.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # with global permissions
        rule = Rule.get_by_("study", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post(
            f"/api/study/{study.id}/organization",
            headers=headers,
            json={"id": org3.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json), len(study.organizations))

        # global permission should still not allow organization to be added to study
        # if it is not part of the collaboration
        results = self.app.post(
            f"/api/study/{study.id}/organization",
            headers=headers,
            json={"id": org_outside_collab.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        org_outside_collab.delete()
        col.delete()
        study.delete()

    def test_delete_study_organization_permissions(self):
        org = Organization()
        org2 = Organization()
        org3 = Organization()
        org_outside_collab = Organization()
        col = Collaboration(organizations=[org, org2, org3])
        study = Study(collaboration=col, organizations=[org, org2])
        study.save()

        # try to do it without permission
        headers = self.get_user_auth_header()
        results = self.app.delete(
            f"/api/study/{study.id}/organization",
            headers=headers,
            json={"id": org.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # delete first organization with root permission
        rule = Rule.get_by_("study", Scope.GLOBAL, Operation.EDIT)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(
            f"/api/study/{study.id}/organization",
            headers=headers,
            json={"id": org.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json), 1)  # 1 organization left

        # add back first organization
        study.organizations.append(org)
        study.save()

        # removing organization from study from outside the collaboration should fail
        # with collaboration permission
        rule = Rule.get_by_(
            "study", scope=Scope.COLLABORATION, operation=Operation.EDIT
        )
        headers = self.get_user_auth_header(
            organization=org_outside_collab, rules=[rule]
        )
        results = self.app.delete(
            f"/api/study/{study.id}/organization",
            headers=headers,
            json={"id": org.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test removing organization from study from within the collaboration with
        # collaboration level permission should work
        headers = self.get_user_auth_header(organization=org3, rules=[rule])
        results = self.app.delete(
            f"/api/study/{study.id}/organization",
            headers=headers,
            json={"id": org.id},
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        org.delete()
        org2.delete()
        org3.delete()
        org_outside_collab.delete()
        col.delete()
        study.delete()

    def test_view_study_node_permissions(self):
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        node = Node(collaboration=col, organization=org)
        node.save()
        study = Study(collaboration=col, organizations=[org])
        study.save()

        # try to view without any permissions
        headers = self.get_user_auth_header()
        results, json_data = self.paginated_list(
            "/api/node?collaboration_id=9999", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view from another collaboration with collaboration permission
        rule = Rule.get_by_("node", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/node?study_id={study.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # try to view from another organization with global permissions
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results, json_data = self.paginated_list(
            f"/api/node?study_id={study.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(study.organizations))

        # view nodes from the study now with collaboration permissions
        rule = Rule.get_by_("node", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule], organization=org2)
        results, json_data = self.paginated_list(
            f"/api/node?study_id={study.id}", headers=headers
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(json_data), len(study.organizations))

        # cleanup
        node.delete()
        org.delete()
        org2.delete()
        col.delete()
        study.delete()
