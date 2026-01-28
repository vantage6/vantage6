"""
Unit tests for the GA4GH Task Execution Service (TES) API endpoints.

These tests verify that the TES API responses conform to the GA4GH TES
specification structure.
"""
import unittest
import json
import uuid
import yaml

from http import HTTPStatus
from unittest.mock import patch
from flask import Response as BaseResponse
from flask.testing import FlaskClient
from flask_socketio import SocketIO
from werkzeug.utils import cached_property

from vantage6.common.globals import APPNAME, InstanceType
from vantage6.common.task_status import TaskStatus
from vantage6.common.serialization import serialize
from vantage6.common import bytes_to_base64s
from vantage6.backend.common import test_context
from vantage6.server.globals import PACKAGE_FOLDER
from vantage6.server import ServerApp
from vantage6.server.model import (
    Rule,
    Organization,
    User,
    Node,
    Collaboration,
    Task,
    Run,
)
from vantage6.server.model.rule import Scope, Operation
from vantage6.server.model.base import Database, DatabaseSessionManager
from vantage6.server.controller.fixture import load


class Response(BaseResponse):
    @cached_property
    def json(self):
        return json.loads(self.data)


class TestNode(FlaskClient):
    def open(self, *args, **kwargs):
        if "json" in kwargs:
            kwargs["data"] = json.dumps(kwargs.pop("json"))
            kwargs["content_type"] = "application/json"
        return super().open(*args, **kwargs)


TES_STATES = [
    "UNKNOWN",
    "QUEUED",
    "INITIALIZING",
    "RUNNING",
    "PAUSED",
    "COMPLETE",
    "EXECUTOR_ERROR",
    "SYSTEM_ERROR",
    "CANCELED",
    "CANCELING",
    "PREEMPTED",
]


class TestTesApi(unittest.TestCase):
    """Test cases for the TES API endpoints."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        Database().connect("sqlite://", allow_drop_all=True)

        ctx = test_context.TestContext.from_external_config_file(
            PACKAGE_FOLDER, InstanceType.SERVER
        )

        with patch.object(SocketIO, "start_background_task"):
            server = ServerApp(ctx)
        cls.server = server

        file_ = str(
            PACKAGE_FOLDER / APPNAME / "server" / "_data" / "unittest_fixtures.yaml"
        )
        with open(file_) as f:
            cls.entities = yaml.safe_load(f.read())
        load(cls.entities)

        server.app.testing = True
        cls.app = server.app.test_client()

        cls.credentials = {
            "root": {"username": "root", "password": "root"},
            "admin": {"username": "frank-iknl", "password": "password"},
            "user": {"username": "melle-iknl", "password": "password"},
        }

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()

    def setUp(self):
        DatabaseSessionManager.get_session()

    def tearDown(self):
        DatabaseSessionManager.clear_session()

    def login(self, type_="root"):
        """Login and return authorization headers."""
        with self.server.app.test_client() as client:
            tokens = client.post("/api/token/user", json=self.credentials[type_]).json
        if "access_token" in tokens:
            return {"Authorization": f"Bearer {tokens['access_token']}"}
        return None

    def create_user_and_login(self, organization=None, rules=None):
        """Create a test user and return login headers."""
        if rules is None:
            rules = []
        if not organization:
            organization = Organization(name=str(uuid.uuid1()))
            organization.save()

        username = str(uuid.uuid1())
        password = "password"
        user = User(
            username=username,
            password=password,
            organization=organization,
            email=f"{username}@test.org",
            rules=rules,
        )
        user.save()
        self.credentials[username] = {"username": username, "password": password}
        return self.login(username)

    def create_test_task(self):
        """Create a test task with runs for testing."""
        org = Organization(name=str(uuid.uuid1()))
        org.save()
        col = Collaboration(name=str(uuid.uuid1()), organizations=[org], encrypted=False)
        col.save()
        node = Node(
            name=str(uuid.uuid1()),
            api_key=str(uuid.uuid1()),
            organization=org,
            collaboration=col,
        )
        node.save()

        task = Task(
            name="test-task",
            description="Test task description",
            image="test-image:latest",
            collaboration=col,
            init_org=org,
        )
        task.save()

        run = Run(
            task=task,
            organization=org,
            input=bytes_to_base64s(serialize({"method": "test"})),
            status=TaskStatus.PENDING,
        )
        run.save()

        return task, org, col, node, run

    # =========================================================================
    # Service Info Endpoint Tests
    # =========================================================================
    def test_service_info_returns_200(self):
        """Test that service-info endpoint returns 200 OK."""
        headers = self.login("root")
        result = self.app.get("/ga4gh/tes/v1/service-info", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

    def test_service_info_structure(self):
        """Test that service-info response has required TES fields."""
        headers = self.login("root")
        result = self.app.get("/ga4gh/tes/v1/service-info", headers=headers)
        data = result.json

        required_fields = ["id", "name", "type", "version"]
        for field in required_fields:
            self.assertIn(field, data, f"Missing required field: {field}")

        self.assertIn("type", data)
        type_fields = ["group", "artifact", "version"]
        for field in type_fields:
            self.assertIn(field, data["type"], f"Missing type field: {field}")

        self.assertEqual(data["type"]["group"], "org.ga4gh")
        self.assertEqual(data["type"]["artifact"], "tes")

    def test_service_info_optional_fields(self):
        """Test that service-info includes expected optional fields."""
        headers = self.login("root")
        result = self.app.get("/ga4gh/tes/v1/service-info", headers=headers)
        data = result.json

        optional_fields = ["description", "organization", "storage"]
        for field in optional_fields:
            self.assertIn(field, data, f"Missing optional field: {field}")

        if data.get("organization"):
            self.assertIn("name", data["organization"])
            self.assertIn("url", data["organization"])

    # =========================================================================
    # List Tasks Endpoint Tests
    # =========================================================================
    def test_list_tasks_returns_200(self):
        """Test that list tasks endpoint returns 200 OK."""
        headers = self.login("root")
        result = self.app.get("/ga4gh/tes/v1/tasks", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

    def test_list_tasks_structure(self):
        """Test that list tasks response has correct structure."""
        headers = self.login("root")
        result = self.app.get("/ga4gh/tes/v1/tasks", headers=headers)
        data = result.json

        self.assertIn("tasks", data)
        self.assertIsInstance(data["tasks"], list)

    def test_list_tasks_minimal_view(self):
        """Test that MINIMAL view returns only id and state."""
        task, org, col, node, run = self.create_test_task()

        try:
            headers = self.login("root")
            result = self.app.get(
                "/ga4gh/tes/v1/tasks?view=MINIMAL", headers=headers
            )
            data = result.json

            self.assertIn("tasks", data)
            if data["tasks"]:
                task_data = data["tasks"][0]
                self.assertIn("id", task_data)
                self.assertIn("state", task_data)
                self.assertIn(task_data["state"], TES_STATES)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_list_tasks_basic_view(self):
        """Test that BASIC view includes additional fields."""
        task, org, col, node, run = self.create_test_task()

        try:
            headers = self.login("root")
            result = self.app.get(
                "/ga4gh/tes/v1/tasks?view=BASIC", headers=headers
            )
            data = result.json

            self.assertIn("tasks", data)
            if data["tasks"]:
                task_data = data["tasks"][0]
                self.assertIn("id", task_data)
                self.assertIn("state", task_data)
                basic_fields = ["name", "description", "executors", "creation_time"]
                for field in basic_fields:
                    self.assertIn(
                        field, task_data, f"BASIC view missing field: {field}"
                    )
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_list_tasks_full_view(self):
        """Test that FULL view includes logs."""
        task, org, col, node, run = self.create_test_task()

        try:
            headers = self.login("root")
            result = self.app.get(
                "/ga4gh/tes/v1/tasks?view=FULL", headers=headers
            )
            data = result.json

            self.assertIn("tasks", data)
            if data["tasks"]:
                task_data = data["tasks"][0]
                self.assertIn("logs", task_data)
                self.assertIsInstance(task_data["logs"], list)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_list_tasks_pagination(self):
        """Test that pagination works correctly."""
        headers = self.login("root")
        result = self.app.get(
            "/ga4gh/tes/v1/tasks?page_size=1", headers=headers
        )
        data = result.json

        self.assertIn("tasks", data)
        self.assertLessEqual(len(data["tasks"]), 1)

    def test_list_tasks_state_filter(self):
        """Test filtering by state."""
        headers = self.login("root")
        result = self.app.get(
            "/ga4gh/tes/v1/tasks?state=QUEUED", headers=headers
        )
        data = result.json

        self.assertIn("tasks", data)
        for task_data in data["tasks"]:
            self.assertEqual(task_data["state"], "QUEUED")

    def test_list_tasks_name_prefix_filter(self):
        """Test filtering by name prefix."""
        task, org, col, node, run = self.create_test_task()

        try:
            headers = self.login("root")
            result = self.app.get(
                "/ga4gh/tes/v1/tasks?name_prefix=test", headers=headers
            )
            data = result.json

            self.assertIn("tasks", data)
            self.assertEqual(result.status_code, HTTPStatus.OK)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    # =========================================================================
    # Get Task Endpoint Tests
    # =========================================================================
    def test_get_task_returns_200(self):
        """Test that get task endpoint returns 200 OK for existing task."""
        task, org, col, node, run = self.create_test_task()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}", headers=headers
            )
            self.assertEqual(result.status_code, HTTPStatus.OK)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_get_task_returns_404_for_nonexistent(self):
        """Test that get task returns 404 for non-existent task."""
        headers = self.login("root")
        result = self.app.get("/ga4gh/tes/v1/tasks/99999", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

    def test_get_task_invalid_id(self):
        """Test that get task returns 400 for invalid task ID."""
        headers = self.login("root")
        result = self.app.get("/ga4gh/tes/v1/tasks/invalid", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

    def test_get_task_minimal_structure(self):
        """Test that get task with MINIMAL view has correct structure."""
        task, org, col, node, run = self.create_test_task()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}?view=MINIMAL", headers=headers
            )
            data = result.json

            self.assertIn("id", data)
            self.assertIn("state", data)
            self.assertEqual(data["id"], str(task.id))
            self.assertIn(data["state"], TES_STATES)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_get_task_basic_structure(self):
        """Test that get task with BASIC view has correct structure."""
        task, org, col, node, run = self.create_test_task()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}?view=BASIC", headers=headers
            )
            data = result.json

            required_fields = ["id", "state", "name", "executors"]
            for field in required_fields:
                self.assertIn(field, data, f"Missing required field: {field}")

            self.assertIsInstance(data["executors"], list)
            if data["executors"]:
                executor = data["executors"][0]
                self.assertIn("image", executor)
                self.assertIn("command", executor)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_get_task_full_structure(self):
        """Test that get task with FULL view has correct structure."""
        task, org, col, node, run = self.create_test_task()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}?view=FULL", headers=headers
            )
            data = result.json

            self.assertIn("logs", data)
            self.assertIsInstance(data["logs"], list)

            if data["logs"]:
                log_entry = data["logs"][0]
                self.assertIn("logs", log_entry)
                self.assertIsInstance(log_entry["logs"], list)
                if log_entry["logs"]:
                    executor_log = log_entry["logs"][0]
                    self.assertIn("exit_code", executor_log)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_get_task_state_mapping_pending(self):
        """Test that pending vantage6 tasks map to QUEUED TES state."""
        task, org, col, node, run = self.create_test_task()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}", headers=headers
            )
            data = result.json

            self.assertEqual(data["state"], "QUEUED")
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_get_task_state_mapping_completed(self):
        """Test that completed vantage6 tasks map to COMPLETE TES state."""
        task, org, col, node, run = self.create_test_task()
        run.status = TaskStatus.COMPLETED
        run.save()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}", headers=headers
            )
            data = result.json

            self.assertEqual(data["state"], "COMPLETE")
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_get_task_state_mapping_active(self):
        """Test that active vantage6 tasks map to RUNNING TES state."""
        task, org, col, node, run = self.create_test_task()
        run.status = TaskStatus.ACTIVE
        run.save()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}", headers=headers
            )
            data = result.json

            self.assertEqual(data["state"], "RUNNING")
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_get_task_state_mapping_crashed(self):
        """Test that crashed vantage6 tasks map to EXECUTOR_ERROR TES state."""
        task, org, col, node, run = self.create_test_task()
        run.status = TaskStatus.CRASHED
        run.save()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}", headers=headers
            )
            data = result.json

            self.assertEqual(data["state"], "EXECUTOR_ERROR")
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_get_task_state_mapping_killed(self):
        """Test that killed vantage6 tasks map to CANCELED TES state."""
        task, org, col, node, run = self.create_test_task()
        run.status = TaskStatus.KILLED
        run.save()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}", headers=headers
            )
            data = result.json

            self.assertEqual(data["state"], "CANCELED")
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    # =========================================================================
    # Create Task Endpoint Tests
    # =========================================================================
    def test_create_task_returns_200(self):
        """Test that create task returns 200 OK with valid input."""
        org = Organization(name=str(uuid.uuid1()))
        org.save()
        col = Collaboration(
            name=str(uuid.uuid1()), organizations=[org], encrypted=False
        )
        col.save()
        node = Node(
            name=str(uuid.uuid1()),
            api_key=str(uuid.uuid1()),
            organization=org,
            collaboration=col,
        )
        node.save()

        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.CREATE)
        headers = self.create_user_and_login(organization=org, rules=[rule])

        task_json = {
            "name": "test-tes-task",
            "executors": [{"image": "test-image:latest", "command": []}],
            "tags": {"vantage6_collaboration_id": str(col.id)},
            "inputs": [
                {
                    "name": f"input_org_{org.id}",
                    "path": f"/vantage6/input/{org.id}",
                    "content": bytes_to_base64s(serialize({"method": "test"})),
                }
            ],
        }

        try:
            result = self.app.post(
                "/ga4gh/tes/v1/tasks", headers=headers, json=task_json
            )
            self.assertEqual(result.status_code, HTTPStatus.OK)
        finally:
            for task in Task.get():
                for run in task.runs:
                    run.delete()
                task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_create_task_response_structure(self):
        """Test that create task response has correct structure."""
        org = Organization(name=str(uuid.uuid1()))
        org.save()
        col = Collaboration(
            name=str(uuid.uuid1()), organizations=[org], encrypted=False
        )
        col.save()
        node = Node(
            name=str(uuid.uuid1()),
            api_key=str(uuid.uuid1()),
            organization=org,
            collaboration=col,
        )
        node.save()

        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.CREATE)
        headers = self.create_user_and_login(organization=org, rules=[rule])

        task_json = {
            "name": "test-tes-task",
            "executors": [{"image": "test-image:latest", "command": []}],
            "tags": {"vantage6_collaboration_id": str(col.id)},
            "inputs": [
                {
                    "name": f"input_org_{org.id}",
                    "path": f"/vantage6/input/{org.id}",
                    "content": bytes_to_base64s(serialize({"method": "test"})),
                }
            ],
        }

        try:
            result = self.app.post(
                "/ga4gh/tes/v1/tasks", headers=headers, json=task_json
            )
            data = result.json

            self.assertIn("id", data)
            self.assertIsInstance(data["id"], str)
            int(data["id"])
        finally:
            for task in Task.get():
                for run in task.runs:
                    run.delete()
                task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_create_task_missing_executors(self):
        """Test that create task fails without executors."""
        headers = self.login("root")
        task_json = {
            "name": "test-task",
            "tags": {"vantage6_collaboration_id": "1"},
        }

        result = self.app.post(
            "/ga4gh/tes/v1/tasks", headers=headers, json=task_json
        )
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

    def test_create_task_missing_image(self):
        """Test that create task fails without executor image."""
        headers = self.login("root")
        task_json = {
            "name": "test-task",
            "executors": [{"command": ["echo", "hello"]}],
            "tags": {"vantage6_collaboration_id": "1"},
        }

        result = self.app.post(
            "/ga4gh/tes/v1/tasks", headers=headers, json=task_json
        )
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

    def test_create_task_missing_collaboration(self):
        """Test that create task fails without collaboration_id."""
        headers = self.login("root")
        task_json = {
            "name": "test-task",
            "executors": [{"image": "test:latest", "command": []}],
        }

        result = self.app.post(
            "/ga4gh/tes/v1/tasks", headers=headers, json=task_json
        )
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

    def test_create_task_with_backend_parameters(self):
        """Test that create task works with backend_parameters."""
        org = Organization(name=str(uuid.uuid1()))
        org.save()
        col = Collaboration(
            name=str(uuid.uuid1()), organizations=[org], encrypted=False
        )
        col.save()
        node = Node(
            name=str(uuid.uuid1()),
            api_key=str(uuid.uuid1()),
            organization=org,
            collaboration=col,
        )
        node.save()

        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.CREATE)
        headers = self.create_user_and_login(organization=org, rules=[rule])

        task_json = {
            "name": "test-tes-task",
            "executors": [{"image": "test-image:latest", "command": []}],
            "resources": {
                "backend_parameters": {
                    "vantage6_collaboration_id": str(col.id),
                    "vantage6_organization_ids": str(org.id),
                }
            },
        }

        try:
            result = self.app.post(
                "/ga4gh/tes/v1/tasks", headers=headers, json=task_json
            )
            self.assertEqual(result.status_code, HTTPStatus.OK)
        finally:
            for task in Task.get():
                for run in task.runs:
                    run.delete()
                task.delete()
            node.delete()
            col.delete()
            org.delete()

    # =========================================================================
    # Cancel Task Endpoint Tests
    # =========================================================================
    def test_cancel_task_returns_200(self):
        """Test that cancel task returns 200 OK for running task."""
        task, org, col, node, run = self.create_test_task()
        run.status = TaskStatus.ACTIVE
        run.save()

        rule = Rule.get_by_("event", Scope.GLOBAL, Operation.SEND)
        headers = self.create_user_and_login(organization=org, rules=[rule])

        try:
            result = self.app.post(
                f"/ga4gh/tes/v1/tasks/{task.id}:cancel", headers=headers
            )
            self.assertEqual(result.status_code, HTTPStatus.OK)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_cancel_task_response_structure(self):
        """Test that cancel task returns empty object."""
        task, org, col, node, run = self.create_test_task()
        run.status = TaskStatus.ACTIVE
        run.save()

        rule = Rule.get_by_("event", Scope.GLOBAL, Operation.SEND)
        headers = self.create_user_and_login(organization=org, rules=[rule])

        try:
            result = self.app.post(
                f"/ga4gh/tes/v1/tasks/{task.id}:cancel", headers=headers
            )
            data = result.json

            self.assertIsInstance(data, dict)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_cancel_task_returns_404_for_nonexistent(self):
        """Test that cancel task returns 404 for non-existent task."""
        rule = Rule.get_by_("event", Scope.GLOBAL, Operation.SEND)
        headers = self.create_user_and_login(rules=[rule])

        result = self.app.post(
            "/ga4gh/tes/v1/tasks/99999:cancel", headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

    def test_cancel_task_returns_400_for_completed(self):
        """Test that cancel task returns 400 for already completed task."""
        task, org, col, node, run = self.create_test_task()
        run.status = TaskStatus.COMPLETED
        run.save()

        rule = Rule.get_by_("event", Scope.GLOBAL, Operation.SEND)
        headers = self.create_user_and_login(organization=org, rules=[rule])

        try:
            result = self.app.post(
                f"/ga4gh/tes/v1/tasks/{task.id}:cancel", headers=headers
            )
            self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_cancel_task_invalid_id(self):
        """Test that cancel task returns 400 for invalid task ID."""
        rule = Rule.get_by_("event", Scope.GLOBAL, Operation.SEND)
        headers = self.create_user_and_login(rules=[rule])

        result = self.app.post(
            "/ga4gh/tes/v1/tasks/invalid:cancel", headers=headers
        )
        self.assertEqual(result.status_code, HTTPStatus.BAD_REQUEST)

    # =========================================================================
    # Authentication Tests
    # =========================================================================
    def test_endpoints_require_authentication(self):
        """Test that all TES endpoints require authentication."""
        endpoints = [
            ("GET", "/ga4gh/tes/v1/service-info"),
            ("GET", "/ga4gh/tes/v1/tasks"),
            ("POST", "/ga4gh/tes/v1/tasks"),
            ("GET", "/ga4gh/tes/v1/tasks/1"),
            ("POST", "/ga4gh/tes/v1/tasks/1:cancel"),
        ]

        for method, url in endpoints:
            if method == "GET":
                result = self.app.get(url)
            else:
                result = self.app.post(url, json={})

            self.assertIn(
                result.status_code,
                [HTTPStatus.UNAUTHORIZED, HTTPStatus.UNPROCESSABLE_ENTITY],
                f"Endpoint {method} {url} should require authentication",
            )

    # =========================================================================
    # Tags Structure Tests
    # =========================================================================
    def test_task_tags_structure(self):
        """Test that task tags are properly formatted."""
        task, org, col, node, run = self.create_test_task()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}?view=BASIC", headers=headers
            )
            data = result.json

            self.assertIn("tags", data)
            self.assertIsInstance(data["tags"], dict)
            self.assertIn("vantage6_collaboration_id", data["tags"])
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    # =========================================================================
    # Inputs/Outputs Structure Tests
    # =========================================================================
    def test_task_inputs_structure(self):
        """Test that task inputs are properly formatted."""
        task, org, col, node, run = self.create_test_task()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}?view=BASIC", headers=headers
            )
            data = result.json

            self.assertIn("inputs", data)
            self.assertIsInstance(data["inputs"], list)

            if data["inputs"]:
                input_item = data["inputs"][0]
                self.assertIn("path", input_item)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()

    def test_task_outputs_structure(self):
        """Test that task outputs are properly formatted."""
        task, org, col, node, run = self.create_test_task()
        run.result = bytes_to_base64s(serialize({"result": "test"}))
        run.status = TaskStatus.COMPLETED
        run.save()

        try:
            headers = self.login("root")
            result = self.app.get(
                f"/ga4gh/tes/v1/tasks/{task.id}?view=BASIC", headers=headers
            )
            data = result.json

            self.assertIn("outputs", data)
            self.assertIsInstance(data["outputs"], list)

            if data["outputs"]:
                output_item = data["outputs"][0]
                self.assertIn("path", output_item)
                self.assertIn("url", output_item)
        finally:
            run.delete()
            task.delete()
            node.delete()
            col.delete()
            org.delete()


if __name__ == "__main__":
    unittest.main()
