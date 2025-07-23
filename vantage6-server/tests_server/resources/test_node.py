import logging
import uuid
from http import HTTPStatus
from unittest.mock import patch

from vantage6.common import logger_name
from vantage6.backend.common.auth import KeycloakServiceAccount
from vantage6.server.model import (
    Rule,
    Organization,
    Node,
    Collaboration,
    Study,
)
from vantage6.server.model.rule import Scope, Operation
from .test_resource_base import TestResourceBase


logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):

    @patch("vantage6.server.resource.node.create_service_account_in_keycloak")
    def test_node_without_id(self, mock_create_node_in_keycloak):
        mock_create_node_in_keycloak.return_value = KeycloakServiceAccount(
            client_id=str(uuid.uuid1()),
            client_secret=str(uuid.uuid1()),
            user_id=str(uuid.uuid1()),
        )

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
        node = self.create_node()
        rule = Rule.get_by_("node", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.get(f"/api/node/{node.id}", headers=headers).json
        expected_fields = [
            "name",
            "collaboration",
            "organization",
            "status",
            "id",
            "type",
            "last_seen",
        ]
        for key in expected_fields:
            self.assertIn(key, result)

        # user cannot access all
        headers = self.get_user_auth_header()
        node = self.app.get(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(node.status_code, HTTPStatus.UNAUTHORIZED)

        # some nodes just don't exist
        node = self.app.get("/api/node/9999", headers=headers)
        self.assertEqual(node.status_code, 404)

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
        node = self.create_node(org, col)

        headers = self.login_node(node)

        # global permissions
        results = self.app.get(f"/api/node/{node.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # list organization permissions
        results = self.app.get("/api/node", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), len(org.nodes))

        # cleanup
        node.delete()

    @patch("vantage6.server.resource.node.create_service_account_in_keycloak")
    def test_create_node_permissions(self, mock_create_node_in_keycloak):
        mock_create_node_in_keycloak.return_value = KeycloakServiceAccount(
            client_id=str(uuid.uuid1()),
            client_secret=str(uuid.uuid1()),
            user_id=str(uuid.uuid1()),
        )

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

    @patch("vantage6.server.resource.node.delete_service_account_in_keycloak")
    def test_delete_node_permissions(self, mock_delete_node_in_keycloak):
        mock_delete_node_in_keycloak.return_value = None

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
