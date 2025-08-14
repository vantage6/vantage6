import logging
from http import HTTPStatus

from vantage6.common import logger_name

from vantage6.backend.common import session as db_session

from vantage6.server.model import (
    Collaboration,
    Organization,
    Role,
    Rule,
)
from vantage6.server.model.rule import Operation, Scope

from .test_resource_base import TestResourceBase

logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):
    def test_view_roles(self):
        headers = self.login_as_root()
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
        headers = self.login_as_root()
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
        headers = self.login(user)
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
        headers = self.login_as_root()

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
        headers = self.login_as_root()

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
        headers = self.login_as_root()
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
        headers = self.login_as_root()

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
        role2 = Role(name="some-role-name", organization=org3)
        role2.save()
        result = self.app.patch(
            f"/api/role/{role2.id}",
            headers=headers,
            json={"name": "this-will-not-be-updated"},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        role.delete()
        role2.delete()

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
