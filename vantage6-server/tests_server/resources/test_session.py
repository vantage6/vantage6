from http import HTTPStatus
from uuid import uuid1

from vantage6.server.model import Session, User
from vantage6.server.model.collaboration import Collaboration
from vantage6.server.model.organization import Organization
from vantage6.server.model.rule import Operation, Rule, Scope

from .test_resource_base import TestResourceBase


class TestSessionResource(TestResourceBase):
    def create_session(
        self, user=None, organization=None, collaboration=None, scope=Scope.OWN
    ):
        if not organization:
            organization = Organization(name=str(uuid1()))
            organization.save()
        if not user:
            user = User(username=str(uuid1()), organization=organization)
            user.save()
        if not collaboration:
            collaboration = Collaboration(
                name=str(uuid1()), organizations=[organization]
            )
            collaboration.save()

        session = Session(
            name=str(uuid1()),
            collaboration_id=collaboration.id,
            scope=scope.value,
            owner=user,
        )
        session.save()

        return session

    def test_get_session(self):
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

    def test_create_session(self):
        organization = Organization(name=str(uuid1()))
        organization.save()
        collaboration = Collaboration(name=str(uuid1()), organizations=[organization])
        collaboration.save()
        user = User(
            username=str(uuid1()),
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
            "name": str(uuid1()),
            "collaboration_id": collaboration.id,
            "scope": "own",
        }
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == HTTPStatus.CREATED

        session = Session.get(response.json["id"])
        self.assertEqual(session.name, session_input["name"])
        self.assertEqual(session.scope, session_input["scope"])

    def test_get_session_id(self):
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

    def test_update_session(self):
        organization = Organization(name=str(uuid1()))
        organization.save()
        collaboration = Collaboration(name=str(uuid1()), organizations=[organization])
        collaboration.save()
        user = User(
            username=str(uuid1()),
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
            "name": str(uuid1()),
            "scope": "own",
        }
        response = self.app.patch(
            f"/api/session/{session.id}", json=session_input, headers=headers
        )
        assert response.status_code == HTTPStatus.OK

        session = Session.get(session.id)
        self.assertEqual(session.name, session_input["name"])
        self.assertEqual(session.scope, session_input["scope"])

        session.delete()

    def test_delete_session(self):
        session = self.create_session()
        headers = self.login_as_root()
        response = self.app.delete(f"/api/session/{session.id}", headers=headers)
        assert response.status_code == HTTPStatus.OK

        session = Session.get(session.id)
        self.assertIsNone(session)

    def test_view_session_permissions(self):
        organization = Organization(name=str(uuid1()))
        organization.save()
        organization2 = Organization(name=str(uuid1()))
        organization2.save()
        collaboration = Collaboration(
            name=str(uuid1()), organizations=[organization, organization2]
        )
        collaboration.save()
        user = User(username=str(uuid1()), organization=organization)
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

        # check that the user that create the session can see the sessions
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
