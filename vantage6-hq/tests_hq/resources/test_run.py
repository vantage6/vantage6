import logging
from http import HTTPStatus

from vantage6.common import logger_name
from vantage6.common.enum import AlgorithmStepType, RunStatus

from vantage6.server.model import (
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
