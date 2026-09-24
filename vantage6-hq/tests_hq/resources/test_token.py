from http import HTTPStatus

from vantage6.common.enum import AlgorithmStepType, RunStatus

from vantage6.hq.model import (
    Collaboration,
    Organization,
    Run,
    Task,
)

from .test_resource_base import TestResourceBase


class TestResources(TestResourceBase):
    def test_container_token_denied_for_unassigned_node(self):
        # a central compute task assigned to org_a; a node from a different
        # organization in the same collaboration must not be able to obtain a
        # container token for it
        org_a = Organization()
        org_b = Organization()
        col = Collaboration(organizations=[org_a, org_b])
        task = Task(collaboration=col, image="some-image", init_org=org_a)
        task.save()
        Run(
            task=task,
            organization=org_a,
            status=RunStatus.PENDING.value,
            action=AlgorithmStepType.CENTRAL_COMPUTE.value,
        ).save()

        node_b = self.create_node(organization=org_b, collaboration=col)
        headers = self.login_node(node_b)

        result = self.app.post(
            "/api/token/container",
            headers=headers,
            json={"image": "some-image", "task_id": task.id},
        )
        self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

    def test_container_token_granted_for_assigned_node(self):
        org_a = Organization()
        org_b = Organization()
        col = Collaboration(organizations=[org_a, org_b])
        task = Task(collaboration=col, image="some-image", init_org=org_a)
        task.save()
        Run(
            task=task,
            organization=org_a,
            status=RunStatus.PENDING.value,
            action=AlgorithmStepType.CENTRAL_COMPUTE.value,
        ).save()

        node_a = self.create_node(organization=org_a, collaboration=col)
        headers = self.login_node(node_a)

        result = self.app.post(
            "/api/token/container",
            headers=headers,
            json={"image": "some-image", "task_id": task.id},
        )
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertIn("container_token", result.json)

    def test_container_token_multi_run_assignment(self):
        # a central compute task can have multiple runs (one per assigned
        # organization); the check must consider all of them, not just the
        # first or last run
        org_a = Organization()
        org_b = Organization()
        org_c = Organization()
        col = Collaboration(organizations=[org_a, org_b, org_c])
        task = Task(collaboration=col, image="some-image", init_org=org_a)
        task.save()
        Run(
            task=task,
            organization=org_a,
            status=RunStatus.PENDING.value,
            action=AlgorithmStepType.CENTRAL_COMPUTE.value,
        ).save()
        Run(
            task=task,
            organization=org_c,
            status=RunStatus.PENDING.value,
            action=AlgorithmStepType.CENTRAL_COMPUTE.value,
        ).save()

        node_a = self.create_node(organization=org_a, collaboration=col)
        node_b = self.create_node(organization=org_b, collaboration=col)
        node_c = self.create_node(organization=org_c, collaboration=col)

        result_a = self.app.post(
            "/api/token/container",
            headers=self.login_node(node_a),
            json={"image": "some-image", "task_id": task.id},
        )
        self.assertEqual(result_a.status_code, HTTPStatus.OK)

        result_c = self.app.post(
            "/api/token/container",
            headers=self.login_node(node_c),
            json={"image": "some-image", "task_id": task.id},
        )
        self.assertEqual(result_c.status_code, HTTPStatus.OK)

        result_b = self.app.post(
            "/api/token/container",
            headers=self.login_node(node_b),
            json={"image": "some-image", "task_id": task.id},
        )
        self.assertEqual(result_b.status_code, HTTPStatus.UNAUTHORIZED)
