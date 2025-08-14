from http import HTTPStatus
from unittest.mock import patch
from uuid import uuid4

from vantage6.common.enum import AlgorithmStepType

from vantage6.server.model import Session, User
from vantage6.server.model.collaboration import Collaboration
from vantage6.server.model.dataframe import Dataframe
from vantage6.server.model.organization import Organization
from vantage6.server.model.rule import Operation, Rule, Scope
from vantage6.server.model.study import Study

from .test_resource_base import TestResourceBase


class TestSessionResource(TestResourceBase):
    """Test /session resource"""

    def test_get(self):
        session = self.create_session()
        headers = self.login_as_root()
        sessions_response = self.app.get("/api/session", headers=headers)
        assert sessions_response.status_code == HTTPStatus.OK

        data = sessions_response.json["data"][0]
        self.assertEqual(data["name"], session.name)
        self.assertEqual(data["scope"], session.scope)
        self.assertEqual(data["owner"]["id"], session.owner.id)
        self.assertEqual(data["collaboration"]["id"], session.collaboration_id)
        self.assertEqual(data["study"], None)
        self.assertEqual(data["image"], None)
        self.assertIn("last_used_at", data)
        self.assertIn("created_at", data)
        self.assertEqual(data["ready"], False)

    def test_create(self):
        organization = Organization(name=str(uuid4()))
        organization.save()
        collaboration = Collaboration(name=str(uuid4()), organizations=[organization])
        collaboration.save()
        user = User(
            username=str(uuid4()),
            organization=organization,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.COLLABORATION,
                    operation=Operation.CREATE,
                )
            ],
        )
        user.save()

        headers = self.login(user)
        session_input = {
            "name": str(uuid4()),
            "collaboration_id": collaboration.id,
            "scope": "own",
        }
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.CREATED

        session = Session.get(response.json["id"])
        self.assertEqual(session.name, session_input["name"])
        self.assertEqual(session.scope, session_input["scope"])

        # test that creating the session again with the same name will fail
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.BAD_REQUEST

        # test that you don't need to provide a name
        session_input = {
            "collaboration_id": collaboration.id,
            "scope": "own",
        }
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.CREATED

        # test that creating a session fails for a study that doesn't exist
        session_input["study_id"] = str(uuid4())
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.BAD_REQUEST

        # test that creating a session fails for a study that is not part of the
        # collaboration
        collaboration2 = Collaboration(name=str(uuid4()), organizations=[organization])
        collaboration2.save()
        study = Study(name=str(uuid4()), collaboration=collaboration2)
        study.save()
        session_input["study_id"] = study.id
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.BAD_REQUEST

        # test that creating a session with a study that is part of the collaboration
        # succeeds
        study = Study(name=str(uuid4()), collaboration=collaboration)
        study.save()
        session_input["study_id"] = study.id
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.CREATED

    def test_get_single(self):
        session = self.create_session()
        headers = self.login_as_root()
        response = self.app.get(f"/api/session/{session.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        data = response.json
        self.assertEqual(data["name"], session.name)
        self.assertEqual(data["scope"], session.scope)
        self.assertEqual(data["owner"]["id"], session.owner.id)
        self.assertEqual(data["collaboration"]["id"], session.collaboration_id)
        self.assertEqual(data["study"], None)
        self.assertEqual(data["image"], None)
        self.assertIn("last_used_at", data)
        self.assertIn("created_at", data)
        self.assertEqual(data["ready"], False)

    def test_update(self):
        organization = Organization(name=str(uuid4()))
        organization.save()
        collaboration = Collaboration(name=str(uuid4()), organizations=[organization])
        collaboration.save()
        user = User(
            username=str(uuid4()),
            organization=organization,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.COLLABORATION,
                    operation=Operation.EDIT,
                )
            ],
        )
        user.save()
        session = self.create_session(user, organization, collaboration)
        headers = self.login(user)
        session_input = {
            "name": str(uuid4()),
            "scope": "own",
        }
        response = self.app.patch(
            f"/api/session/{session.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK

        session = Session.get(session.id)
        self.assertEqual(session.name, session_input["name"])
        self.assertEqual(session.scope, session_input["scope"])

        # test that session cannot be updated to the name of another session
        ses_name = "name-exists"
        other_session = self.create_session(
            user, organization, collaboration, name=ses_name
        )
        other_session.save()
        session_input["name"] = ses_name
        response = self.app.patch(
            f"/api/session/{session.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

        # non-existing session
        response = self.app.patch(
            "/api/session/9999", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.NOT_FOUND

        # non-existing scope
        session_input["scope"] = "non-existing"
        response = self.app.patch(
            f"/api/session/{session.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

    def test_delete(self):
        session = self.create_session()
        headers = self.login_as_root()
        response = self.app.delete(f"/api/session/{session.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        session = Session.get(session.id)
        self.assertIsNone(session)

        # non-existing session
        response = self.app.delete("/api/session/9999", headers=headers)
        assert response.status_code == HTTPStatus.NOT_FOUND

        # test delete_dependents
        session = self.create_session()
        dataframe = Dataframe(name=str(uuid4()), session=session)
        dataframe.save()
        df_id = dataframe.id
        ses_id = session.id
        response = self.app.delete(f"/api/session/{session.id}", headers=headers)
        assert response.status_code == HTTPStatus.BAD_REQUEST
        response = self.app.delete(
            f"/api/session/{session.id}?delete_dependents=true", headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        assert Dataframe.get(df_id) is None
        assert Session.get(ses_id) is None

    def test_view_permissions(self):
        organization = Organization(name=str(uuid4()))
        organization.save()
        organization2 = Organization(name=str(uuid4()))
        organization2.save()
        collaboration = Collaboration(
            name=str(uuid4()), organizations=[organization, organization2]
        )
        collaboration.save()
        user = User(username=str(uuid4()), organization=organization)
        user.save()

        session_own = self.create_session(user, organization, collaboration)
        session_org = self.create_session(
            user, organization, collaboration, Scope.ORGANIZATION
        )
        session_col = self.create_session(
            user, organization, collaboration, Scope.COLLABORATION
        )

        # check that root user can see all sessions
        headers = self.login_as_root()
        response = self.app.get("/api/session", headers=headers)
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 3

        # check that user without any permissions can not see any sessions
        headers = self.create_user_and_login()
        response = self.app.get("/api/session", headers=headers)
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 0

        # check that the user that created the session can see the sessions
        headers = self.login(user)
        response = self.app.get("/api/session", headers=headers)
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 3

        # check that a user from the same organization can see all sessions except the
        # one with scope OWN
        headers = self.create_user_and_login(organization=organization)
        response = self.app.get("/api/session", headers=headers)
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 2
        assert session_org.id in [s["id"] for s in response.json["data"]]
        assert session_col.id in [s["id"] for s in response.json["data"]]
        assert session_own.id not in [s["id"] for s in response.json["data"]]

        # check that a user from another organization can see the collaboration level
        # sessions
        headers = self.create_user_and_login(organization=organization2)
        response = self.app.get("/api/session", headers=headers)
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1
        assert response.json["data"][0]["id"] == session_col.id

        # Check that if we give user from another organization the permissions to see
        # all sessions on collaboration level, they can see the all sessions the first
        # user created
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
        response = self.app.get("/api/session", headers=headers)
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 3

        # check that a user from the same organization with organization level
        # permissions can also see the scope=own session (and the other sessions)
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
        response = self.app.get("/api/session", headers=headers)
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 3

        # check that for a user from another organization with organization level
        # permissions, they cannot see the scope=own session nor the scope=organization
        # session, but only the scope=collaboration session
        headers = self.create_user_and_login(
            organization=organization2,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.ORGANIZATION,
                    operation=Operation.VIEW,
                )
            ],
        )
        response = self.app.get("/api/session", headers=headers)
        assert response.status_code == HTTPStatus.OK
        assert len(response.json["data"]) == 1

    def test_view_single_permissions(self):
        organization = Organization(name=str(uuid4()))
        organization.save()
        organization2 = Organization(name=str(uuid4()))
        organization2.save()
        collaboration = Collaboration(
            name=str(uuid4()), organizations=[organization, organization2]
        )
        collaboration.save()
        user = User(username=str(uuid4()), organization=organization)
        user.save()

        session_own = self.create_session(user, organization, collaboration)
        session_org = self.create_session(
            user, organization, collaboration, Scope.ORGANIZATION
        )
        session_col = self.create_session(
            user, organization, collaboration, Scope.COLLABORATION
        )

        # check that user without any permissions outside the collaboration can not see
        # any sessions
        headers = self.create_user_and_login()
        response = self.app.get(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(f"/api/session/{session_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(f"/api/session/{session_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that the user that created the sessions can see all of them
        headers = self.login(user)
        response = self.app.get(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.get(f"/api/session/{session_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.get(f"/api/session/{session_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        # create another user in the organization. This user should not be able to see
        # the session if the scope is own, but should be able to see the session if the
        # scope is organization or collaboration
        headers = self.create_user_and_login(organization=organization)
        response = self.app.get(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(f"/api/session/{session_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.get(f"/api/session/{session_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        # create another user in the collaboration but in another organization. This
        # user should not be able to see the session if the scope is own or
        # organization, but should be able to see the session if the scope is
        # collaboration
        headers = self.create_user_and_login(organization=organization2)
        response = self.app.get(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(f"/api/session/{session_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.get(f"/api/session/{session_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        # now get a user from the same organization but with organization level
        # permissions. They should now also be able to see the session if the scope is
        # own
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
        response = self.app.get(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        # a user from another organization with collaboration level permissions should
        # be able to see all the sessions
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
        response = self.app.get(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.get(f"/api/session/{session_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.get(f"/api/session/{session_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

    def test_create_permissions(self):
        organization = Organization(name=str(uuid4()))
        organization.save()
        organization2 = Organization(name=str(uuid4()))
        organization2.save()
        collaboration = Collaboration(
            name=str(uuid4()), organizations=[organization, organization2]
        )
        collaboration.save()

        # check that user without any permissions CANNOT create session with scope=own
        session_input = {
            "collaboration_id": collaboration.id,
            "scope": Scope.OWN.value,
        }
        headers = self.create_user_and_login(organization=organization)
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that user without any permissions CANNOT create session with scope=
        # organization
        session_input["scope"] = Scope.ORGANIZATION.value
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that user without any permissions CANNOT create session with scope=
        # collaboration
        session_input["scope"] = Scope.COLLABORATION.value
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that user with own level permissions CAN create session with scope=own
        headers = self.create_user_and_login(
            organization=organization,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.OWN,
                    operation=Operation.CREATE,
                )
            ],
        )
        session_input["scope"] = Scope.OWN.value
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.CREATED

        # check that user with own level permissions CANNOT create session with scope=
        # organization
        session_input["scope"] = Scope.ORGANIZATION.value
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that user with own level permissions CANNOT create session with scope=
        # collaboration
        session_input["scope"] = Scope.COLLABORATION.value
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that user with organization level permissions CAN create session with
        # scope=organization
        headers = self.create_user_and_login(
            organization=organization,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.ORGANIZATION,
                    operation=Operation.CREATE,
                )
            ],
        )
        session_input["scope"] = Scope.ORGANIZATION.value
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.CREATED

        # check that user with organization level permissions CANNOT create session with
        # scope=collaboration
        session_input["scope"] = Scope.COLLABORATION.value
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that user with organization level permissions CAN create session with
        # scope=organization
        session_input["scope"] = Scope.ORGANIZATION.value
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.CREATED

        # check that user with collaboration level permissions CAN create session with
        # scope=collaboration
        headers = self.create_user_and_login(
            organization=organization,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.COLLABORATION,
                    operation=Operation.CREATE,
                )
            ],
        )
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.CREATED

        # test that even root user cannot create session within collaboration they are
        # not part of
        headers = self.login_as_root()
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_edit_permissions(self):
        organization = Organization(name=str(uuid4()))
        organization.save()
        organization2 = Organization(name=str(uuid4()))
        organization2.save()
        collaboration = Collaboration(
            name=str(uuid4()), organizations=[organization, organization2]
        )
        collaboration.save()
        user = User(username=str(uuid4()), organization=organization)
        user.save()

        session_own = self.create_session(user, organization, collaboration)
        session_org = self.create_session(
            user, organization, collaboration, Scope.ORGANIZATION
        )
        session_col = self.create_session(
            user, organization, collaboration, Scope.COLLABORATION
        )

        # test that you cannot edit session without permissions
        session_input = {"name": str(uuid4())}
        headers = self.login(user)
        response = self.app.patch(
            f"/api/session/{session_own.id}",
            json=session_input,
            headers=headers,
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # test that user can edit their own session if they have own level permissions
        user.rules = [
            Rule.get_by_(
                name="session",
                scope=Scope.OWN,
                operation=Operation.EDIT,
            )
        ]
        user.save()
        headers = self.login(user)
        response = self.app.patch(
            f"/api/session/{session_own.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK

        # test that user cannot edit the session if the scope is organization or above,
        # even if they created the session themselves
        session_input["name"] = str(uuid4())
        response = self.app.patch(
            f"/api/session/{session_org.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.patch(
            f"/api/session/{session_col.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that this user cannot edit the scope of the session above scope=own
        session_input["scope"] = Scope.ORGANIZATION.value
        response = self.app.patch(
            f"/api/session/{session_own.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        session_input["scope"] = Scope.COLLABORATION.value
        response = self.app.patch(
            f"/api/session/{session_own.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        session_input["scope"] = Scope.OWN.value

        # check that another user within the organization cannot edit the session
        # with OWN scope
        headers = self.create_user_and_login(
            organization=organization,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.OWN,
                    operation=Operation.EDIT,
                )
            ],
        )
        session_input["name"] = str(uuid4())
        response = self.app.patch(
            f"/api/session/{session_own.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # test that with organization level permissions, the user can edit the session
        # if the scope is organization or above
        headers = self.create_user_and_login(
            organization=organization,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.ORGANIZATION,
                    operation=Operation.EDIT,
                )
            ],
        )
        session_input["name"] = str(uuid4())
        response = self.app.patch(
            f"/api/session/{session_own.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        session_input["name"] = str(uuid4())
        response = self.app.patch(
            f"/api/session/{session_org.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        response = self.app.patch(
            f"/api/session/{session_col.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # check that they can edit the scope of the session from org to own and vice
        # versa
        del session_input["name"]
        session_input["scope"] = Scope.OWN.value
        response = self.app.patch(
            f"/api/session/{session_org.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        session_input["scope"] = Scope.ORGANIZATION.value
        response = self.app.patch(
            f"/api/session/{session_own.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        session_input["scope"] = Scope.COLLABORATION.value
        response = self.app.patch(
            f"/api/session/{session_org.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        # change back scopes
        session_own.scope = Scope.OWN
        session_own.save()
        session_org.scope = Scope.ORGANIZATION
        session_org.save()
        del session_input["scope"]

        # test that user within collaboration but from other organization cannot edit
        # the session
        headers = self.create_user_and_login(
            organization=organization2,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.ORGANIZATION,
                    operation=Operation.EDIT,
                )
            ],
        )
        session_input["name"] = str(uuid4())
        response = self.app.patch(
            f"/api/session/{session_org.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # test that user with collaboration level permissions can edit each session
        headers = self.create_user_and_login(
            organization=organization2,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.COLLABORATION,
                    operation=Operation.EDIT,
                )
            ],
        )
        session_input["name"] = str(uuid4())
        response = self.app.patch(
            f"/api/session/{session_own.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        session_input["name"] = str(uuid4())
        response = self.app.patch(
            f"/api/session/{session_org.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        session_input["name"] = str(uuid4())
        response = self.app.patch(
            f"/api/session/{session_col.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        del session_input["name"]

        # test that user with collaboration level permissions can edit the scope of the
        # session
        session_input["scope"] = Scope.COLLABORATION.value
        response = self.app.patch(
            f"/api/session/{session_own.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        session_input["scope"] = Scope.COLLABORATION.value
        response = self.app.patch(
            f"/api/session/{session_org.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        session_input["scope"] = Scope.ORGANIZATION.value
        response = self.app.patch(
            f"/api/session/{session_col.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK
        # change back scopes
        session_own.scope = Scope.OWN
        session_own.save()
        session_org.scope = Scope.ORGANIZATION
        session_org.save()
        session_col.scope = Scope.COLLABORATION
        session_col.save()
        del session_input["scope"]

    def test_delete_permissions(self):
        organization = Organization(name=str(uuid4()))
        organization.save()
        organization2 = Organization(name=str(uuid4()))
        organization2.save()
        collaboration = Collaboration(
            name=str(uuid4()), organizations=[organization, organization2]
        )
        collaboration.save()
        user = User(username=str(uuid4()), organization=organization)
        user.save()

        session_own = self.create_session(user, organization, collaboration)
        session_org = self.create_session(
            user, organization, collaboration, Scope.ORGANIZATION
        )
        session_col = self.create_session(
            user, organization, collaboration, Scope.COLLABORATION
        )

        # test that you cannot delete session without permissions
        headers = self.login(user)
        response = self.app.delete(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # test that with own level permissions, you can delete your own session, but not
        # the other sessions
        user.rules = [
            Rule.get_by_(
                name="session",
                scope=Scope.OWN,
                operation=Operation.DELETE,
            )
        ]
        user.save()
        headers = self.login(user)
        response = self.app.delete(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.delete(f"/api/session/{session_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        response = self.app.delete(f"/api/session/{session_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        # recreate session
        session_own = self.create_session(user, organization, collaboration)

        # test that another user within the organization cannot delete the session
        # with OWN scope
        headers = self.create_user_and_login(
            organization=organization,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.OWN,
                    operation=Operation.DELETE,
                )
            ],
        )
        response = self.app.delete(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # test that another user within the organization can delete the session
        # with ORGANIZATION scope
        headers = self.create_user_and_login(
            organization=organization,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.ORGANIZATION,
                    operation=Operation.DELETE,
                )
            ],
        )
        response = self.app.delete(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.delete(f"/api/session/{session_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.delete(f"/api/session/{session_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        # recreate sessions
        session_own = self.create_session(user, organization, collaboration)
        session_org = self.create_session(user, organization, collaboration)

        # test that a user in another organization cannot delete the session with
        # ORGANIZATION scope
        headers = self.create_user_and_login(
            organization=organization2,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.ORGANIZATION,
                    operation=Operation.DELETE,
                )
            ],
        )
        response = self.app.delete(f"/api/session/{session_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.UNAUTHORIZED

        # test that another user within the collaboration can delete the session
        # with COLLABORATION scope
        headers = self.create_user_and_login(
            organization=organization2,
            rules=[
                Rule.get_by_(
                    name="session",
                    scope=Scope.COLLABORATION,
                    operation=Operation.DELETE,
                )
            ],
        )
        response = self.app.delete(f"/api/session/{session_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.delete(f"/api/session/{session_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.delete(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        # recreate sessions
        session_own = self.create_session(user, organization, collaboration)
        session_org = self.create_session(user, organization, collaboration)
        session_col = self.create_session(user, organization, collaboration)

        # test that root user can delete all sessions
        headers = self.login_as_root()
        response = self.app.delete(f"/api/session/{session_own.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.delete(f"/api/session/{session_org.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK
        response = self.app.delete(f"/api/session/{session_col.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

    @patch(
        "vantage6.server.resource.common.task_post_base.TaskPostBase"
        "._check_arguments_encryption"
    )
    @patch(
        "vantage6.server.resource.common.task_post_base.TaskPostBase"
        "._check_data_extract_ready_for_requested_orgs"
    )
    # pylint: disable=unused-argument
    def test_session_restrict_to_same_image(
        self,
        mock_check_arguments_encryption,
        mock_check_data_extract_ready_for_requested_orgs,
    ):
        org = self.create_organization()
        col = self.create_collaboration(organizations=[org], restrict_image=True)
        user = self.create_user(organization=org, rules=Rule.get())
        session = self.create_session(user=user, collaboration=col)
        headers = self.login(user)

        # first, initialize the session with a dataframe
        create_dataframe_input = {
            "label": "dummy-db-label",
            "task": {
                "image": "dummy-image",
                "method": "dummy-method",
                "organizations": [{"id": org.id}],
            },
        }
        response = self.app.post(
            f"/api/session/{session.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.CREATED
        df = Dataframe.get(response.json["id"])

        # now, try to create a dataframe with a different image
        create_dataframe_input["task"]["image"] = "dummy-image-2"
        response = self.app.post(
            f"/api/session/{session.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

        # check that we CAN create another dataframe with the same image
        create_dataframe_input["label"] = "dummy-db-label-2"
        create_dataframe_input["task"]["image"] = "dummy-image"
        response = self.app.post(
            f"/api/session/{session.id}/dataframe",
            headers=headers,
            json=create_dataframe_input,
        )
        assert response.status_code == HTTPStatus.CREATED

        # try to create a preprocess task with a different image
        create_preprocess_input = {
            "dataframe_id": df.id,
            "task": {
                "image": "dummy-image-2",
                "method": "dummy-method",
                "organizations": [{"id": org.id}],
            },
        }
        response = self.app.post(
            f"/api/session/dataframe/{df.id}/preprocess",
            headers=headers,
            json=create_preprocess_input,
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST

        # check that we CAN create a preprocess task with the same image
        create_preprocess_input["task"]["image"] = "dummy-image"
        response = self.app.post(
            f"/api/session/dataframe/{df.id}/preprocess",
            headers=headers,
            json=create_preprocess_input,
        )
        assert response.status_code == HTTPStatus.CREATED

        # check that we can also create a compute task with the same image
        task_json = {
            "image": "dummy-image",
            "method": "dummy",
            "collaboration_id": col.id,
            "organizations": [{"id": org.id}],
            "session_id": session.id,
            "action": AlgorithmStepType.FEDERATED_COMPUTE.value,
        }
        response = self.app.post("/api/task", headers=headers, json=task_json)
        assert response.status_code == HTTPStatus.CREATED

        # but not with a different image
        task_json["image"] = "dummy-image-2"
        response = self.app.post("/api/task", headers=headers, json=task_json)
        assert response.status_code == HTTPStatus.BAD_REQUEST

        # if we disable the check, we can create a task with a different image
        col.session_restrict_to_same_image = False
        col.save()
        response = self.app.post("/api/task", headers=headers, json=task_json)
        assert response.status_code == HTTPStatus.CREATED
