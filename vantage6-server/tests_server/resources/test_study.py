import logging
from http import HTTPStatus

from vantage6.common import logger_name
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
