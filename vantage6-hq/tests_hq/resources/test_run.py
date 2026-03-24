import datetime
import logging
import uuid
from http import HTTPStatus

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
        task = Task()
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
        org1 = Organization("test-org-1")
        org2 = Organization(name=str(uuid.uuid1()))
        col = Collaboration(name=str(uuid.uuid1()), organizations=[org1, org2])
        col.save()

        node1, api_key1 = self.create_node(organization=org1, collaboration=col)
        node2, _ = self.create_node(organization=org2, collaboration=col)

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
            started_at=datetime.datetime.now(datetime.timezone.utc),
        )
        finished_sibling = Run(
            task=task,
            organization=org2,
            status=RunStatus.COMPLETED.value,
            finished_at=datetime.datetime.now(datetime.timezone.utc),
        )
        failing_run.save()
        pending_sibling.save()
        started_sibling.save()
        finished_sibling.save()

        try:
            headers = self.login_node(api_key1)
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
