import logging
import uuid
from http import HTTPStatus

from vantage6.common import logger_name
from vantage6.server.model import (
    Rule,
    Organization,
    Node,
    Collaboration,
)
from vantage6.server.model.rule import Scope, Operation
from .test_resource_base import TestResourceBase


logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):

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

    def test_view_organization_as_user_permissions(self):
        # view without any permissions
        headers = self.get_user_auth_header()
        result = self.app.get("/api/organization", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # view your own organization
        rule = Rule.get_by_("organization", Scope.ORGANIZATION, Operation.VIEW)
        user = self.create_user(rules=[rule])
        headers = self.login(user)
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
        node = self.create_node()
        headers = self.login_node(node)

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
        node = self.create_node()
        headers = self.login_container(node=node)

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
