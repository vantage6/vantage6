from uuid import uuid1

from vantage6.server.model import Session, User, Node

from .test_resource_base import TestResourceBase


class TestSessionResource(TestResourceBase):

    def create_session(self, user=None):
        if not user:
            user = User.get_by_username("root")

        session = Session(
            name=str(uuid1()), collaboration_id=1, scope="OWN", owner=user
        )
        session.save()

        return session

    def test_get_session(self):
        session = self.create_session()
        headers = self.login()
        sessions_response = self.app.get("/api/session", headers=headers)
        assert sessions_response.status_code == 200

        data = sessions_response.json["data"][0]
        self.assertEqual(data["name"], session.name)
        self.assertEqual(data["scope"], session.scope)
        self.assertIn("owner", data)
        self.assertIn("collaboration", data)
        self.assertIn("tasks", data)
        self.assertIn("last_used_at", data)
        self.assertIn("created_at", data)
        self.assertIn("ready", data)
        self.assertIn("node_sessions", data)

        session.delete()

    def test_create_session(self):
        headers = self.login()
        session_input = {
            "name": str(uuid1()),
            "collaboration_id": 1,
            "scope": "own",
        }
        response = self.app.post("/api/session", json=session_input, headers=headers)
        assert response.status_code == 201

        session = Session.get(response.json["id"])
        self.assertEqual(session.name, session_input["name"])
        self.assertEqual(session.scope, session_input["scope"])

        session.delete()

    def test_get_session_id(self):
        session = self.create_session()
        headers = self.login()
        response = self.app.get(f"/api/session/{session.id}", headers=headers)
        assert response.status_code == 200

        data = response.json
        self.assertEqual(data["name"], session.name)
        self.assertEqual(data["scope"], session.scope)
        self.assertIn("owner", data)
        self.assertIn("collaboration", data)
        self.assertIn("tasks", data)
        self.assertIn("last_used_at", data)
        self.assertIn("created_at", data)
        self.assertIn("ready", data)
        self.assertIn("node_sessions", data)

        session.delete()

    def test_update_session(self):
        session = self.create_session()
        headers = self.login()
        session_input = {
            "name": str(uuid1()),
            "scope": "own",
        }
        response = self.app.patch(
            f"/api/session/{session.id}", json=session_input, headers=headers
        )
        assert response.status_code == 200

        session = Session.get(session.id)
        self.assertEqual(session.name, session_input["name"])
        self.assertEqual(session.scope, session_input["scope"])

        session.delete()

    def test_delete_session(self):
        session = self.create_session()
        headers = self.login()
        response = self.app.delete(f"/api/session/{session.id}", headers=headers)
        assert response.status_code == 200

        session = Session.get(session.id)
        self.assertIsNone(session)

    def test_get_node_sessions(self):
        headers = self.login()
        session_rep = self.app.post(
            "/api/session",
            json={"name": str(uuid1()), "collaboration_id": 1, "scope": "own"},
            headers=headers,
        )

        session = Session.get(session_rep.json["id"])
        for n_session in session.node_sessions:
            self.addCleanup(n_session.delete)
        self.addCleanup(session.delete)

        response = self.app.get(f"/api/session/{session.id}/node", headers=headers)
        assert response.status_code == 200

        data = response.json
        self.assertGreater(len(data), 0)
        self.assertEqual(len(data), len(session.node_sessions))

    def test_update_node_sessions(self):

        # API key is coming from the unittest.yaml file
        node = Node.get_by_api_key("123e4567-e89b-12d3-a456-426614174000")
        collaboration_id = node.collaboration_id

        headers = self.login()
        session_rep = self.app.post(
            "/api/session",
            json={
                "name": str(uuid1()),
                "collaboration_id": collaboration_id,
                "scope": "own",
            },
            headers=headers,
        )

        session = Session.get(session_rep.json["id"])
        for n_session in session.node_sessions:
            for n_session_config in n_session.config:
                self.addCleanup(n_session_config.delete)
            self.addCleanup(n_session.delete)
        self.addCleanup(session.delete)

        headers = self.login_node(api_key="123e4567-e89b-12d3-a456-426614174000")
        response = self.app.patch(
            f"/api/session/{session.id}/node",
            json={
                "state": "ready",
                "config": [{"key": "test-key", "value": "test-value"}],
            },
            headers=headers,
        )
        assert response.status_code == 200

        # data = response.json
        # conf = data["config"][0]
