from http import HTTPStatus
from unittest.mock import patch
from uuid import uuid4

from vantage6.server.model.collaboration import Collaboration
from vantage6.server.model.organization import Organization
from vantage6.server.model.rule import Operation, Rule, Scope

from .test_resource_base import TestResourceBase


class TestDataframe(TestResourceBase):
    """Test /dataframe resource"""

    def test_get(self):
        session = self.create_session()
        df = self.create_dataframe(session=session, collaboration=session.collaboration)
        headers = self.login_as_root()
        response = self.app.get(f"/api/session/{session.id}/dataframe", headers=headers)
        assert response.status_code == HTTPStatus.OK
        data = response.json["data"][0]
        assert data["id"] == df.id
        assert data["name"] == df.name
        assert "db_label" in data
        assert "session" in data
        assert "tasks" in data
        assert "last_session_task" in data
        assert "columns" in data
        assert "ready" in data
        assert "organizations_ready" in data

    def test_view_permissions(self):
        organization = Organization(name=str(uuid4()))
        organization.save()
        organization2 = Organization(name=str(uuid4()))
        organization2.save()
        collaboration = Collaboration(
            name=str(uuid4()), organizations=[organization, organization2]
        )
        collaboration.save()
        user = self.create_user(organization=organization)
        session_own = self.create_session(user, organization, collaboration)
        session_org = self.create_session(
            user, organization, collaboration, Scope.ORGANIZATION
        )
        session_col = self.create_session(
            user, organization, collaboration, Scope.COLLABORATION
        )
        df_own = self.create_dataframe(session=session_own, collaboration=collaboration)
        df_org = self.create_dataframe(session=session_org, collaboration=collaboration)
        df_col = self.create_dataframe(session=session_col, collaboration=collaboration)

        # check that root user can see all dataframes
        headers = self.login_as_root()
        response = self.app.get(
            f"/api/session/{session_own.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1
        response = self.app.get(
            f"/api/session/{session_org.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1
        response = self.app.get(
            f"/api/session/{session_col.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1

        # check that user without any permissions can not see any dataframes
        headers = self.create_user_and_login()
        response = self.app.get(
            f"/api/session/{session_own.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(
            f"/api/session/{session_org.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(
            f"/api/session/{session_col.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that the user that created the sessions can see the dataframes
        headers = self.login(user)
        response = self.app.get(
            f"/api/session/{session_own.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1
        response = self.app.get(
            f"/api/session/{session_org.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1
        response = self.app.get(
            f"/api/session/{session_col.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1

        # check that a user from the same organization can see all dataframes except the
        # one with scope OWN
        headers = self.create_user_and_login(organization=organization)
        response = self.app.get(
            f"/api/session/{session_own.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(
            f"/api/session/{session_org.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1
        assert df_org.id in [d["id"] for d in response.json["data"]]
        response = self.app.get(
            f"/api/session/{session_col.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1

        # check that a user from another organization can see only the collaboration
        # level dataframes
        headers = self.create_user_and_login(organization=organization2)
        response = self.app.get(
            f"/api/session/{session_own.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(
            f"/api/session/{session_org.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(
            f"/api/session/{session_col.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1

        # check that explicit view-org permissions allow seeing the scope=own dataframe
        headers = self.create_user_and_login(
            organization=organization,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.ORGANIZATION,
                    operation=Operation.VIEW,
                )
            ],
        )
        response = self.app.get(
            f"/api/session/{session_own.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1
        assert df_own.id in [d["id"] for d in response.json["data"]]

        # check that explicit view-col permissions allow seeing the scope=org,own data
        headers = self.create_user_and_login(
            organization=organization2,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.COLLABORATION,
                    operation=Operation.VIEW,
                )
            ],
        )
        response = self.app.get(
            f"/api/session/{session_own.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1
        response = self.app.get(
            f"/api/session/{session_org.id}/dataframe", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1

    def test_get_single(self):
        org = self.create_organization()
        collaboration = self.create_collaboration(organizations=[org])
        user = self.create_user(organization=org)
        session = self.create_session(user=user, collaboration=collaboration)
        df = self.create_dataframe(session=session, collaboration=collaboration)

        headers = self.login(user)
        response = self.app.get(f"/api/session/dataframe/{df.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        data = response.json
        assert data["id"] == df.id
        assert data["name"] == df.name
        assert "columns" in data
        assert "db_label" in data
        assert "last_session_task" in data
        assert "tasks" in data
        assert data["session"]["id"] == session.id
        assert not data["ready"]
        assert data["organizations_ready"] == []

        # check non-existing dataframe
        response = self.app.get("/api/session/dataframe/9999", headers=headers)
        assert response.status_code == HTTPStatus.NOT_FOUND

    def test_view_single_permissions(self):
        org = self.create_organization()
        org2 = self.create_organization()
        collaboration = self.create_collaboration(organizations=[org, org2])
        user = self.create_user(organization=org)

        session_own = self.create_session(user=user, collaboration=collaboration)
        df_own = self.create_dataframe(session=session_own, collaboration=collaboration)

        session_org = self.create_session(
            user=user, collaboration=collaboration, scope=Scope.ORGANIZATION
        )
        df_org = self.create_dataframe(session=session_org, collaboration=collaboration)

        session_col = self.create_session(
            user=user, collaboration=collaboration, scope=Scope.COLLABORATION
        )
        df_col = self.create_dataframe(session=session_col, collaboration=collaboration)

        # check that root user can see all dataframes
        headers = self.login_as_root()
        response = self.app.get(f"/api/session/dataframe/{df_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.get(f"/api/session/dataframe/{df_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.get(f"/api/session/dataframe/{df_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        # check that user without any permissions can not see any dataframes
        headers = self.create_user_and_login()
        response = self.app.get(f"/api/session/dataframe/{df_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(f"/api/session/dataframe/{df_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(f"/api/session/dataframe/{df_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that the user that created the sessions can see the dataframes
        headers = self.login(user)
        response = self.app.get(f"/api/session/dataframe/{df_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.get(f"/api/session/dataframe/{df_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.get(f"/api/session/dataframe/{df_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        # check that a user from the same organization can NOT see the scope=own
        # dataframe but CAN see the scope=org,own dataframe
        headers = self.create_user_and_login(organization=org)
        response = self.app.get(f"/api/session/dataframe/{df_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(f"/api/session/dataframe/{df_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.get(f"/api/session/dataframe/{df_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        # check that a user from another organization can NOT see the scope=org,own
        # dataframe but CAN see the scope=col dataframe
        headers = self.create_user_and_login(organization=org2)
        response = self.app.get(f"/api/session/dataframe/{df_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(f"/api/session/dataframe/{df_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(f"/api/session/dataframe/{df_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        # check that explicit view-org permissions allow seeing the scope=own dataframe
        headers = self.create_user_and_login(
            organization=org,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.ORGANIZATION,
                    operation=Operation.VIEW,
                )
            ],
        )
        response = self.app.get(f"/api/session/dataframe/{df_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        # check that explicit view-col permissions allow seeing the scope=org,own dataframe
        headers = self.create_user_and_login(
            organization=org2,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.COLLABORATION,
                    operation=Operation.VIEW,
                )
            ],
        )
        response = self.app.get(f"/api/session/dataframe/{df_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.get(f"/api/session/dataframe/{df_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

    @patch(
        "vantage6.server.resource.common.task_post_base.TaskPostBase._check_arguments_encryption"
    )
    def test_create(self, mock_check_arguments_encryption):
        org = self.create_organization()
        collaboration = self.create_collaboration(
            organizations=[org], restrict_image=True
        )
        user = self.create_user(
            organization=org,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.ORGANIZATION,
                    operation=Operation.EDIT,
                ),
                Rule.get_by_(
                    name="task",
                    scope=Scope.COLLABORATION,
                    operation=Operation.CREATE,
                ),
            ],
        )
        session = self.create_session(user=user, collaboration=collaboration)
        headers = self.login(user)
        dummy_name = str(uuid4())
        create_dataframe_input = {
            "label": "dummy-db-label",
            "name": dummy_name,
            "task": {
                "image": "dummy-image",
                "method": "dummy-method",
                "organizations": [{"id": org.id}],
            },
        }

        # try for non-existing session
        response = self.app.post(
            "/api/session/9999/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

        # now with the real thing
        response = self.app.post(
            f"/api/session/{session.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.CREATED
        assert response.json["name"] == dummy_name
        assert response.json["db_label"] == "dummy-db-label"
        assert response.json["session"]["id"] == session.id
        assert response.json["last_session_task"]["image"] == "dummy-image"
        assert response.json["last_session_task"]["method"] == "dummy-method"

        # since restrict_image is True, no task should be created with new image
        create_dataframe_input["name"] = dummy_name + "-2"
        create_dataframe_input["task"]["image"] = "dummy-image-2"
        response = self.app.post(
            f"/api/session/{session.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

        # check that we cannot create another dataframe with the same name
        create_dataframe_input["name"] = dummy_name
        create_dataframe_input["task"]["image"] = "dummy-image"
        response = self.app.post(
            f"/api/session/{session.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

        # check that the name was now the only issue
        create_dataframe_input["name"] = "new-dummy-df-name"
        response = self.app.post(
            f"/api/session/{session.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.CREATED

    def test_create_permissions(self):
        org = self.create_organization()
        org2 = self.create_organization()
        collaboration = self.create_collaboration(organizations=[org, org2])
        user = self.create_user(organization=org)

        session_own = self.create_session(user=user, collaboration=collaboration)
        session_org = self.create_session(
            user=user, collaboration=collaboration, scope=Scope.ORGANIZATION
        )
        session_col = self.create_session(
            user=user, collaboration=collaboration, scope=Scope.COLLABORATION
        )

        create_dataframe_input = {
            "label": "dummy-db-label",
            "task": {
                "image": "dummy-image",
                "method": "dummy-method",
                "organizations": [{"id": org.id}],
            },
        }

        # check that user without any permissions can not create dataframe in any of
        # the sessions
        headers = self.login(user)
        response = self.app.post(
            f"/api/session/{session_own.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.post(
            f"/api/session/{session_org.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.post(
            f"/api/session/{session_col.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that user with own level permissions can create dataframe in own session
        create_task_rule = Rule.get_by_(
            name="task",
            scope=Scope.COLLABORATION,
            operation=Operation.CREATE,
        )
        user.rules = [
            Rule.get_by_(
                name="session",
                scope=Scope.OWN,
                operation=Operation.EDIT,
            ),
            create_task_rule,
        ]
        user.save()
        headers = self.login(user)
        response = self.app.post(
            f"/api/session/{session_own.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.CREATED

        # this user should not be able to create dataframe in organization-level session
        # or collaboration-level session
        response = self.app.post(
            f"/api/session/{session_org.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.post(
            f"/api/session/{session_col.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # with organization level permissions, the user should be able to create dataframe
        # in organization-level session
        headers = self.create_user_and_login(
            organization=org,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.ORGANIZATION,
                    operation=Operation.EDIT,
                ),
                create_task_rule,
            ],
        )
        response = self.app.post(
            f"/api/session/{session_own.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.CREATED
        response = self.app.post(
            f"/api/session/{session_org.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.CREATED
        response = self.app.post(
            f"/api/session/{session_col.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # user with collaboration level permissions should not be able to create dataframe
        # in any of the sessions
        headers = self.create_user_and_login(
            organization=org2,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.COLLABORATION,
                    operation=Operation.EDIT,
                ),
                create_task_rule,
            ],
        )
        response = self.app.post(
            f"/api/session/{session_own.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.CREATED
        response = self.app.post(
            f"/api/session/{session_org.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.CREATED
        response = self.app.post(
            f"/api/session/{session_col.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.CREATED

        # check that even root user cannot create dataframe in collaboration they are
        # not part of
        headers = self.login_as_root()
        response = self.app.post(
            f"/api/session/{session_own.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_update(self):
        pass

    def test_edit_permissions(self):
        pass

    def test_delete(self):
        pass

    def test_delete_permissions(self):
        pass

    def test_create_preprocess(self):
        pass

    def test_preprocess_permissions(self):
        pass

    def test_create_columns(self):
        pass

    def test_columns_permissions(self):
        pass
