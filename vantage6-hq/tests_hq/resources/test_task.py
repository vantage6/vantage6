import json
import logging
from http import HTTPStatus
from unittest.mock import MagicMock

from vantage6.common import bytes_to_base64s, logger_name
from vantage6.common.enum import AlgorithmStepType, RunStatus, TaskStatus
from vantage6.common.serialization import serialize

from vantage6.hq.model import (
    Collaboration,
    Node,
    Organization,
    Rule,
    Run,
    Session,
    Study,
    Task,
)
from vantage6.hq.model.rule import Operation, Scope
from vantage6.hq.resource.event import kill_task

from .test_resource_base import TestResourceBase

logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):
    def test_task_with_id(self):
        task = Task(name="unit")
        task.save()
        headers = self.login_as_root()
        result = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_task_witout_id(self):
        headers = self.login_as_root()
        result = self.app.get("/api/task", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_task_including_runs(self):
        headers = self.login_as_root()
        result = self.app.get("/api/task?include=runs", headers=headers)
        self.assertEqual(result.status_code, 200)

    def test_task_unknown(self):
        headers = self.login_as_root()
        result = self.app.get("/api/task/9999", headers=headers)
        self.assertEqual(result.status_code, 404)

    def test_view_task_permissions_as_user(self):
        # non existing task
        headers = self.get_user_auth_header()
        results = self.app.get("/api/task/9999", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # test user without any permissions and id
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        task = Task(name="unit", collaboration=col, init_org=org)
        task.save()

        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test user with col permissions with id
        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(results.json["name"], "unit")

        # collaboration permission outside the collaboration should fail
        org_not_in_collab = Organization()
        org_not_in_collab.save()
        headers = self.get_user_auth_header(
            organization=org_not_in_collab, rules=[rule]
        )
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test user with org permissions with id from another org
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test user with org permissions without id
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test that user is not allowed to view task results without id
        results = self.app.get(
            "/api/task", headers=headers, query_string={"include": "results"}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test that user is allowed to view task results if they have the rule
        # to view results
        rule_view_results = Rule.get_by_("run", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule, rule_view_results])
        results = self.app.get(
            "/api/task", headers=headers, query_string={"include": "results"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test user with global permissions and id
        rule = Rule.get_by_("task", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test that user is not allowed to view task results with id
        results = self.app.get(
            f"/api/task/{task.id}", headers=headers, query_string={"include": "results"}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test that user is allowed to view task results if they have the rule
        # to view results
        headers = self.get_user_auth_header(org, rules=[rule, rule_view_results])
        results = self.app.get(
            f"/api/task/{task.id}", headers=headers, query_string={"include": "results"}
        )
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test user with global permissions without id
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # list collaboration permissions - in collaboration
        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), len(col.tasks))

        # list collaboration permissions - other collaboration
        headers = self.get_user_auth_header(org_not_in_collab, rules=[rule])
        results = self.app.get(
            "/api/task", headers=headers, query_string={"collaboration_id": col.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # list own organization permissions - same organization
        rule = Rule.get_by_("task", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), len(col.tasks))

        # list own organization permissions - other organization
        headers = self.get_user_auth_header(org2, rules=[rule])
        results = self.app.get(
            "/api/task", headers=headers, query_string={"init_org_id": org.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # list own user's task permissions - same user without id
        rule = Rule.get_by_("task", Scope.OWN, Operation.VIEW)
        user = self.create_user(rules=[rule], organization=org)
        headers = self.login(user)
        task2 = Task(name="unit", collaboration=col, init_org=org, init_user=user)
        task2.save()
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertEqual(len(results.json["data"]), 1)

        # list own user's task permissions - same user with id
        results = self.app.get(f"/api/task/{task2.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # list own user's task permissions - other user without id
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.get(
            "/api/task", headers=headers, query_string={"init_user_id": user.id}
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # list own user's task permissions - other user with id
        results = self.app.get(f"/api/task/{task2.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        task.delete()
        task2.delete()
        user.delete()
        org.delete()
        org2.delete()
        col.delete()

    def test_view_task_permissions_as_node_and_container(self):
        # test node with id
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org])
        col.save()
        task = Task(collaboration=col, image="some-image", init_org=org)
        task.save()
        res = Run(
            task=task,
            status=RunStatus.PENDING.value,
            action=AlgorithmStepType.CENTRAL_COMPUTE.value,
        )
        res.save()

        headers = self.create_node_and_login(organization=org)
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test node without id
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test container with id
        headers = self.login_container(collaboration=col, organization=org, task=task)
        results = self.app.get(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test container without id
        results = self.app.get("/api/task", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    def test_create_task_permission_as_user(self):
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org], encrypted=False)
        col.save()
        user = self.create_user(organization=org)
        headers = self.login(user)
        session = Session(name="test_session", user_id=user.id, collaboration=col)
        session.save()

        # test non-existing collaboration
        task_json = {
            "method": "dummy",
            "collaboration_id": 9999,
            "organizations": [{"id": 9999}],
            "image": "some-image",
            "session_id": session.id,
            "action": AlgorithmStepType.FEDERATED_COMPUTE.value,
        }
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.NOT_FOUND)

        # task without any node created
        task_json["organizations"] = [{"id": org.id}]
        task_json["collaboration_id"] = col.id
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # node is used implicitly as in further checks, can only create task
        # if node has been created
        node = Node(organization=org, collaboration=col)
        node.save()
        org2 = Organization()
        org2.save()

        # test user outside the collaboration
        task_json["organizations"] = [{"id": org2.id}]
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # user in the collaboration but still without any permissions
        task_json["organizations"] = [{"id": org.id}]
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # user with organization permissions for other organization
        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.CREATE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.FORBIDDEN)

        # user with organization permissions
        headers = self.get_user_auth_header(org, rules=[rule])
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # user with global permissions but outside of the collaboration. They
        # should *not* be allowed to create a task in a collaboration that
        # they're not a part of
        rule = Rule.get_by_("task", Scope.GLOBAL, Operation.CREATE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.FORBIDDEN)

        # check that no tasks can be created with organizations outside a study but
        # within the collaboration
        col2 = Collaboration(organizations=[org, org2])
        col2.save()
        study = Study(organizations=[org], collaboration=col2)
        study.save()
        task_json["collaboration_id"] = col2.id
        task_json["organizations"] = [{"id": org2.id}]
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # cleanup
        # delete the 1 task that was created in this unit test
        Task.get()[::-1][0].delete()
        session.delete()
        node.delete()
        org.delete()
        org2.delete()
        col.delete()
        col2.delete()
        study.delete()

    def test_create_task_permissions_as_container(self):
        org = Organization()
        col = Collaboration(organizations=[org], encrypted=False)

        user = self.create_user()
        headers = self.login()

        session = Session(name="test_session", user_id=user.id, collaboration=col)
        session.save()

        parent_task = Task(collaboration=col, image="some-image")
        parent_task.save()
        parent_res = Run(
            organization=org,
            task=parent_task,
            status=RunStatus.PENDING.value,
            action=AlgorithmStepType.CENTRAL_COMPUTE.value,
        )
        parent_res.save()

        headers = self.login_container(
            collaboration=col, organization=org, task=parent_task
        )

        # test other collaboration_id
        col2 = Collaboration(organizations=[org])
        col2.save()
        node2 = Node(organization=org, collaboration=col2)
        node2.save()
        task_json = {
            "method": "dummy",
            "organizations": [{"id": org.id}],
            "collaboration_id": col2.id,
            "image": "some-image",
            "session_id": session.id,
            "action": AlgorithmStepType.CENTRAL_COMPUTE.value,
        }

        # Test wrong collaboration_id
        results = self.app.post(
            "/api/task",
            headers=headers,
            json=task_json,
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test actions: task endpoint can also be used for federated compute but not
        # for preprocessing or data extraction
        task_json["action"] = AlgorithmStepType.FEDERATED_COMPUTE.value
        task_json["collaboration_id"] = col.id
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        task_json["action"] = AlgorithmStepType.PREPROCESSING.value
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        task_json["action"] = AlgorithmStepType.DATA_EXTRACTION.value
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # test with correct parameters
        task_json["action"] = AlgorithmStepType.CENTRAL_COMPUTE.value
        results = self.app.post(
            "/api/task",
            headers=headers,
            json=task_json,
        )
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        # test already completed task
        parent_res.status = RunStatus.COMPLETED.value
        parent_res.save()
        results = self.app.post(
            "/api/task",
            headers=headers,
            json=task_json,
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test a failed task
        parent_res.status = RunStatus.FAILED.value
        parent_res.save()
        results = self.app.post(
            "/api/task",
            headers=headers,
            json=task_json,
        )
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        Task.get()[::-1][0].delete()
        session.delete()
        org.delete()
        col.delete()
        node2.delete()
        col2.delete()
        # delete the 1 task that was created in this unit test

    def test_delete_task_permissions(self):
        # test non-existing task
        headers = self.get_user_auth_header()
        self.app.delete("/api/task/9999", headers=headers)

        # test with organization permissions from other organization
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        task = Task(collaboration=col, init_org=org)
        task.save()

        # test with user who is not member of collaboration
        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test with collaboration permissions
        headers = self.get_user_auth_header(org, [rule])
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test with global permissions
        task = Task(collaboration=col)
        task.save()
        rule = Rule.get_by_("task", Scope.GLOBAL, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule])
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test that all results are also deleted
        task = Task(collaboration=col)
        run = Run(task=task)
        run.save()
        run_id = run.id  # cannot access this after deletion
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)
        self.assertIsNone(Task.get(run_id))

        # test permission to delete tasks of own organization - other
        # organization should fail
        task = Task(collaboration=col, init_org=org)
        task.save()
        rule = Rule.get_by_("task", Scope.ORGANIZATION, Operation.DELETE)
        headers = self.get_user_auth_header(rules=[rule], organization=org2)
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test permission to delete tasks of own organization - should work
        headers = self.get_user_auth_header(rules=[rule], organization=org)
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # test permission to delete own tasks - other user of organization
        # should fail
        rule = Rule.get_by_("task", Scope.OWN, Operation.DELETE)
        user = self.create_user(rules=[rule], organization=org)
        task = Task(collaboration=col, init_org=org, init_user=user)
        task.save()
        headers = self.get_user_auth_header(rules=[rule], organization=org)
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.UNAUTHORIZED)

        # test permission to delete own tasks with same user
        headers = self.login(user)
        results = self.app.delete(f"/api/task/{task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

        # cleanup
        user.delete()
        org.delete()
        org2.delete()
        col.delete()

    def test_view_task_result_permissions_as_user(self):
        # non-existing task
        headers = self.get_user_auth_header()
        result = self.app.get("/api/task/9999/run", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # test with organization permissions from other organization
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        col.save()
        task = Task(collaboration=col, init_org=org)
        task.save()
        # NB: node is used implicitly in task/{id}/result schema
        node = Node(organization=org, collaboration=col)
        node.save()
        res = Run(task=task, organization=org)
        res.save()

        # Test with permissions of someone who is not in the collaboration
        rule = Rule.get_by_("run", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test with collaboration permission
        headers = self.get_user_auth_header(org, [rule])
        result = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test with global permission
        rule = Rule.get_by_("run", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test also result endpoint
        rule = Rule.get_by_("run", Scope.COLLABORATION, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.get(f"/api/result?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test result endpoint with organization permission
        headers = self.get_user_auth_header(org, [rule])
        result = self.app.get(f"/api/result?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test result endpoint with global permission
        rule = Rule.get_by_("run", Scope.GLOBAL, Operation.VIEW)
        headers = self.get_user_auth_header(rules=[rule])
        result = self.app.get(f"/api/result?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test with organization permission
        rule = Rule.get_by_("run", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.get_user_auth_header(org, [rule])
        result = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        result = self.app.get(f"/api/run/{res.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test with organization permission - other organization should fail
        headers = self.get_user_auth_header(org2, [rule])
        result = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        result = self.app.get(f"/api/run/{res.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # test with permission to view own runs
        rule = Rule.get_by_("run", Scope.OWN, Operation.VIEW)
        user = self.create_user(rules=[rule], organization=org)
        headers = self.login(user)
        task2 = Task(collaboration=col, init_org=org, init_user=user)
        task2.save()
        res2 = Run(task=task2, organization=org)
        res2.save()
        result = self.app.get(f"/api/run?task_id={task2.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        result = self.app.get(f"/api/run/{res2.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)

        # test with permission to view own runs - other user should fail
        headers = self.get_user_auth_header(rules=[rule], organization=org)
        result = self.app.get(f"/api/run?task_id={task2.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)
        result = self.app.get(f"/api/run/{res2.id}", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        node.delete()
        task.delete()
        task2.delete()
        res.delete()
        res2.delete()
        org.delete()
        org2.delete()
        col.delete()

    def test_get_task_status(self):
        """Test the /api/task/<id>/status endpoint"""

        # Test non-existent task
        headers = self.create_user_and_login()
        result = self.app.get("/api/task/9999/status", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.NOT_FOUND)

        # Create organizations and collaboration
        org = Organization()
        org2 = Organization()
        col = Collaboration(organizations=[org, org2])
        col.save()

        # Create a task
        task = Task(collaboration=col, init_org=org)
        task.save()

        # Add runs to the task with valid statuses
        run1 = Run(task=task, status=RunStatus.ACTIVE.value)
        run2 = Run(task=task, status=RunStatus.PENDING.value)
        run1.save()
        run2.save()

        # Test without permissions
        headers = self.create_user_and_login()
        result = self.app.get(f"/api/task/{task.id}/status", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # Test with collaboration permissions
        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.VIEW)
        headers = self.create_user_and_login(org, rules=[rule])
        result = self.app.get(f"/api/task/{task.id}/status", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(result.json["status"], TaskStatus.WAITING.value)

        # Test with global permissions
        rule = Rule.get_by_("task", Scope.GLOBAL, Operation.VIEW)
        headers = self.create_user_and_login(rules=[rule])
        result = self.app.get(f"/api/task/{task.id}/status", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(result.json["status"], TaskStatus.WAITING.value)

        # Test with organization permissions (should fail for other organizations)
        rule = Rule.get_by_("task", Scope.ORGANIZATION, Operation.VIEW)
        headers = self.create_user_and_login(org2, rules=[rule])
        result = self.app.get(f"/api/task/{task.id}/status", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # Test with organization permissions (should succeed for the same organization)
        headers = self.create_user_and_login(org, rules=[rule])
        result = self.app.get(f"/api/task/{task.id}/status", headers=headers)
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(result.json["status"], TaskStatus.WAITING.value)

        # Cleanup
        task.delete()
        org.delete()
        org2.delete()
        col.delete()

    def test_create_task_with_database_arguments(self):
        org = Organization()
        org.save()
        col = Collaboration(organizations=[org], encrypted=False)
        col.save()
        node = Node(organization=org, collaboration=col)
        node.save()

        rule = Rule.get_by_("task", Scope.COLLABORATION, Operation.CREATE)
        headers = self.create_user_and_login(org, rules=[rule])
        input_ = bytes_to_base64s(serialize({"method": "dummy"}))

        task_json = {
            "collaboration_id": col.id,
            "organizations": [{"id": org.id, "input": input_}],
            "image": "some-image.invalid/invalid:invalid",
            "databases": [
                {
                    "label": "default",
                    "query": "SELECT * FROM records",
                    "arguments": {
                        "bind": "input_dataset",
                        "group": "example",
                    },
                }
            ],
        }
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        first_task = Task.get(results.json["id"])
        self.assertEqual(first_task.databases[0].database, "default")
        self.assertEqual(
            json.loads(first_task.databases[0].parameters),
            {
                "query": "SELECT * FROM records",
                "arguments": {
                    "bind": "input_dataset",
                    "group": "example",
                },
            },
        )

        # arguments must be a dict
        task_json["databases"] = [{"label": "default", "arguments": "dataset"}]
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.BAD_REQUEST)

        # empty arguments are allowed
        task_json["databases"] = [{"label": "default", "arguments": {}}]
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        empty_arguments_task = Task.get(results.json["id"])
        self.assertEqual(
            json.loads(empty_arguments_task.databases[0].parameters),
            {"arguments": {}},
        )

        # omitting arguments is also allowed
        task_json["databases"] = [{"label": "default"}]
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        no_arguments_task = Task.get(results.json["id"])
        self.assertEqual(
            json.loads(no_arguments_task.databases[0].parameters),
            {},
        )

        # multiple databases can each carry their own arguments
        task_json["databases"] = [
            {
                "label": "treatment",
                "arguments": {"bind": "treatment_data"},
            },
            {
                "label": "diagnosis",
                "arguments": {"bind": "diagnosis_data"},
            },
        ]
        results = self.app.post("/api/task", headers=headers, json=task_json)
        self.assertEqual(results.status_code, HTTPStatus.CREATED)

        second_task = Task.get(results.json["id"])
        databases_by_label = {db.database: db for db in second_task.databases}
        self.assertIn("treatment", databases_by_label)
        self.assertIn("diagnosis", databases_by_label)
        self.assertEqual(
            json.loads(databases_by_label["treatment"].parameters),
            {"arguments": {"bind": "treatment_data"}},
        )
        self.assertEqual(
            json.loads(databases_by_label["diagnosis"].parameters),
            {"arguments": {"bind": "diagnosis_data"}},
        )

        first_task.delete()
        empty_arguments_task.delete()
        no_arguments_task.delete()
        second_task.delete()
        node.delete()
        org.delete()
        col.delete()

    def test_kill_task_includes_all_unfinished_child_runs(self):
        # Create a parent task with one run and a child task with three child
        # runs. One of the child runs is already completed and should not be
        # included in the kill payload.
        org_parent = Organization(name="kill-org-parent")
        org_child_1 = Organization(name="kill-org-child-1")
        org_child_2 = Organization(name="kill-org-child-2")
        collaboration = Collaboration(
            name="kill-collaboration",
            organizations=[org_parent, org_child_1, org_child_2],
        )
        collaboration.save()

        parent_task = Task(
            name="parent-task",
            image="parent-image",
            collaboration=collaboration,
            job_id=90001,
        )
        parent_task.save()
        parent_run = Run(
            organization=org_parent, task=parent_task, status=TaskStatus.ACTIVE
        )
        parent_run.save()

        child_task = Task(
            name="child-task",
            image="child-image",
            collaboration=collaboration,
            parent=parent_task,
            job_id=90001,
        )
        child_task.save()
        child_run_1 = Run(
            organization=org_child_1, task=child_task, status=TaskStatus.ACTIVE
        )
        child_run_2 = Run(
            organization=org_child_2, task=child_task, status=TaskStatus.PENDING
        )
        child_run_done = Run(
            organization=org_parent, task=child_task, status=TaskStatus.COMPLETED
        )
        child_run_1.save()
        child_run_2.save()
        child_run_done.save()

        socket = MagicMock()

        kill_task(parent_task, socket)

        # The emitted kill payload should contain every unfinished parent/child
        # run
        emit_args = socket.emit.call_args.args
        kill_list = emit_args[1]["kill_list"]
        self.assertEqual(len(kill_list), 3)
        self.assertCountEqual(
            [entry["run_id"] for entry in kill_list],
            [parent_run.id, child_run_1.id, child_run_2.id],
        )

        self.assertEqual(parent_task.status, TaskStatus.KILLED.value)
        self.assertEqual(child_task.status, TaskStatus.KILLED.value)
        self.assertEqual(parent_run.status, TaskStatus.KILLED)
        self.assertEqual(child_run_1.status, TaskStatus.KILLED)
        self.assertEqual(child_run_2.status, TaskStatus.KILLED)
        self.assertEqual(child_run_done.status, TaskStatus.COMPLETED)
