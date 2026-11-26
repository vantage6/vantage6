import datetime
import logging
import uuid
from http import HTTPStatus
from unittest.mock import patch

from flask_socketio import SocketIO

from vantage6.common import logger_name
from vantage6.common.enum import AlgorithmStepType, RunStatus

from vantage6.hq.model import (
    Collaboration,
    Organization,
    Run,
    Task,
)

from .test_resource_base import TestResourceBase

logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):
    def test_run_without_id(self):
        org = Organization()
        col = Collaboration(organizations=[org])
        task = Task(collaboration=col, init_org=org)
        task.save()

        headers = self.login_as_root()
        result1 = self.app.get("/api/run", headers=headers)
        self.assertEqual(result1.status_code, 200)

        result2 = self.app.get("/api/run?state=open", headers=headers)
        self.assertEqual(result2.status_code, 200)

        result3 = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(result3.status_code, 200)

    def test_view_task_run_permissions_as_container(self):
        # test if container can
        org = Organization()
        col = Collaboration(organizations=[org])
        task = Task(collaboration=col, image="some-image", init_org=org)
        task.save()
        res = Run(
            task=task,
            organization=org,
            status=RunStatus.PENDING.value,
            action=AlgorithmStepType.CENTRAL_COMPUTE.value,
        )
        res.save()

        headers = self.login_container(collaboration=col, organization=org, task=task)
        results = self.app.get(f"/api/run?task_id={task.id}", headers=headers)
        self.assertEqual(results.status_code, HTTPStatus.OK)

    def test_run_patch_fails_pending_siblings(self):
        org1 = Organization(name=str(uuid.uuid1()))
        org2 = Organization(name=str(uuid.uuid1()))
        col = Collaboration(name=str(uuid.uuid1()), organizations=[org1, org2])
        col.save()

        node1 = self.create_node(organization=org1, collaboration=col)
        node2 = self.create_node(organization=org2, collaboration=col)

        task = Task(
            image="localhost/algorithms/test:local",
            collaboration=col,
            init_org=org1,
        )
        task.save()

        failing_run = Run(
            task=task,
            organization=org1,
            status=RunStatus.PENDING.value,
        )
        pending_sibling = Run(
            task=task,
            organization=org2,
            status=RunStatus.PENDING.value,
        )
        started_sibling = Run(
            task=task,
            organization=org2,
            status=RunStatus.PENDING.value,
            started_at=datetime.datetime.now(datetime.UTC),
        )
        finished_sibling = Run(
            task=task,
            organization=org2,
            status=RunStatus.COMPLETED.value,
            finished_at=datetime.datetime.now(datetime.UTC),
        )
        failing_run.save()
        pending_sibling.save()
        started_sibling.save()
        finished_sibling.save()

        try:
            headers = self.login_node(node1)
            response = self.app.patch(
                f"/api/run/{failing_run.id}",
                headers=headers,
                json={"status": RunStatus.FAILED.value},
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)

            pending_sibling = Run.get(pending_sibling.id)
            started_sibling = Run.get(started_sibling.id)
            finished_sibling = Run.get(finished_sibling.id)

            # Sibling runs not yet started shouldn't be in a state that would
            # make it be picked up later (i.e. we want finished_at set)
            self.assertEqual(pending_sibling.status, RunStatus.FAILED.value)
            self.assertIsNone(pending_sibling.started_at)
            self.assertIsNotNone(pending_sibling.finished_at)
            self.assertIn(
                f"sibling run id={failing_run.id} failed",
                pending_sibling.log,
            )

            # Started/finished siblings should not be touched by fail-fast update.
            self.assertEqual(started_sibling.status, RunStatus.PENDING.value)
            self.assertIsNotNone(started_sibling.started_at)
            self.assertIsNone(started_sibling.finished_at)

            self.assertEqual(finished_sibling.status, RunStatus.COMPLETED.value)
            self.assertIsNotNone(finished_sibling.finished_at)
        finally:
            failing_run.delete()
            pending_sibling.delete()
            started_sibling.delete()
            finished_sibling.delete()
            task.delete()
            node1.delete()
            node2.delete()
            col.delete()
            org1.delete()
            org2.delete()

    def test_run_node_other_collaboration_of_same_organization(self):
        org = Organization(name=str(uuid.uuid1()))
        col = Collaboration(name=str(uuid.uuid1()), organizations=[org])
        other_col = Collaboration(name=str(uuid.uuid1()), organizations=[org])
        node = self.create_node(organization=org, collaboration=col)
        self.create_node(organization=org, collaboration=other_col)

        task = Task(collaboration=col, init_org=org, image="some-image")
        other_task = Task(collaboration=other_col, init_org=org, image="some-image")
        run = Run(task=task, organization=org, status=RunStatus.PENDING.value)
        other_run = Run(
            task=other_task, organization=org, status=RunStatus.PENDING.value
        )
        run.save()
        other_run.save()

        headers = self.login_node(node)

        # node cannot patch the run of its sibling node in another collaboration
        response = self.app.patch(
            f"/api/run/{other_run.id}",
            headers=headers,
            json={"status": RunStatus.FAILED.value, "result": "injected"},
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        other_run = Run.get(other_run.id)
        self.assertEqual(other_run.status, RunStatus.PENDING.value)
        self.assertIsNone(other_run.result)

        # node can patch the run of its own collaboration
        response = self.app.patch(
            f"/api/run/{run.id}",
            headers=headers,
            json={"status": RunStatus.ACTIVE.value},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # node cannot view the run of the other collaboration
        response = self.app.get(f"/api/run/{other_run.id}", headers=headers)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        response = self.app.get(f"/api/result/{other_run.id}", headers=headers)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        response = self.app.get("/api/run", headers=headers)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual([r["id"] for r in response.json["data"]], [run.id])
        response = self.app.get(
            f"/api/run?collaboration_id={other_col.id}", headers=headers
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)


class TestRunPatchNotifiesDependentTasks(TestResourceBase):
    def setUp(self):
        super().setUp()
        self.org1 = Organization(name=str(uuid.uuid1()))
        self.org2 = Organization(name=str(uuid.uuid1()))
        self.col = Collaboration(
            name=str(uuid.uuid1()), organizations=[self.org1, self.org2]
        )
        self.col.save()
        self.node1 = self.create_node(organization=self.org1, collaboration=self.col)
        self.node2 = self.create_node(organization=self.org2, collaboration=self.col)

        self.task_a = Task(
            image="some-image", collaboration=self.col, init_org=self.org1
        )
        self.task_a.save()
        self.run_a1 = Run(
            task=self.task_a, organization=self.org1, status=RunStatus.ACTIVE.value
        )
        self.run_a2 = Run(
            task=self.task_a, organization=self.org2, status=RunStatus.ACTIVE.value
        )
        self.run_a1.save()
        self.run_a2.save()

        self.task_b = Task(
            image="some-image",
            collaboration=self.col,
            init_org=self.org1,
            depends_on=[self.task_a],
        )
        self.task_b.save()
        self.run_b = Run(
            task=self.task_b, organization=self.org1, status=RunStatus.PENDING.value
        )
        self.run_b.save()

    def tearDown(self):
        for run in (self.run_b, self.run_a1, self.run_a2):
            run.delete()
        self.task_b.depends_on = []
        self.task_b.save()
        for obj in (
            self.task_b,
            self.task_a,
            self.node1,
            self.node2,
            self.col,
            self.org1,
            self.org2,
        ):
            obj.delete()
        super().tearDown()

    def _patch_run(self, run: Run, node, status: RunStatus) -> list:
        with patch.object(SocketIO, "emit") as mock_emit:
            response = self.app.patch(
                f"/api/run/{run.id}",
                headers=self.login_node(node),
                json={
                    "status": status.value,
                    "finished_at": datetime.datetime.now(datetime.UTC).isoformat(),
                },
            )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        return [c for c in mock_emit.call_args_list if c.args[0] == "new_task_update"]

    def test_notified_when_last_dependency_run_completes(self):
        emits = self._patch_run(self.run_a1, self.node1, RunStatus.COMPLETED)
        self.assertEqual(emits, [])

        emits = self._patch_run(self.run_a2, self.node2, RunStatus.COMPLETED)
        self.assertEqual(len(emits), 1)
        self.assertEqual(emits[0].args[1], {"id": self.task_b.id, "parent_id": None})
        self.assertEqual(emits[0].kwargs["namespace"], "/tasks")
        self.assertEqual(emits[0].kwargs["room"], f"collaboration_{self.col.id}")

    def test_not_notified_when_dependency_fails(self):
        emits = self._patch_run(self.run_a1, self.node1, RunStatus.FAILED)
        self.assertEqual(emits, [])
        self.assertEqual(
            Run.get(self.run_b.id).status, RunStatus.DEPENDED_ON_FAILED_TASK.value
        )
