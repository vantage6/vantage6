import logging
import uuid
from http import HTTPStatus

from vantage6.common import logger_name
from vantage6.server.model import (
    Rule,
    Organization,
    Node,
    Collaboration,
    Task,
)
from vantage6.server.model.rule import Scope, Operation
from .test_resource_base import TestResourceBase


logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):

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
