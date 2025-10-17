import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import call, patch

from sqlalchemy import select

from vantage6.common.enum import RunStatus

from vantage6.server.controller import cleanup
from vantage6.server.model import Task
from vantage6.server.model.base import Database, DatabaseSessionManager
from vantage6.server.model.run import Run


class TestCleanupRunsIsolated(unittest.TestCase):
    def setUp(self):
        Database().connect("sqlite://", allow_drop_all=True)
        self.session = DatabaseSessionManager.get_session()

        self.uuid = str(uuid.uuid4())

    def tearDown(self):
        Database().clear_data()
        Database().close()

    @patch("vantage6.server.model.task.Task")
    def test_cleanup_completed_old_run(self, mock_task):
        # Now use the actual instances, not ints
        task = Task(
            name="test-task",
            description="Test task for cleanup",
            image="test-image:latest",
        )
        self.session.add(task)
        self.session.commit()

        run = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=31),
            result=self.uuid,
            arguments="arguments",
            log="log should be preserved",
            status=RunStatus.COMPLETED.value,
            task=task,
        )

        self.session.add(run)
        self.session.commit()

        cleanup.cleanup_runs_data({"runs_data_cleanup_days": 30}, include_args=True)
        self.session.refresh(run)
        self.assertEqual(run.result, "")
        self.assertEqual(run.arguments, "")
        self.assertEqual(run.log, "log should be preserved")
        self.assertIsNotNone(run.cleanup_at)

    @patch(
        "vantage6.server.service.azure_storage_service.AzureStorageService.delete_blob"
    )
    def test_cleanup_completed_old_blob(self, mock_delete_blob):
        task = Task(
            name="test-task",
            description="Test task for cleanup",
            image="test-image:latest",
        )
        self.session.add(task)
        self.session.commit()

        run = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=31),
            result=self.uuid,
            input="input",
            log="log should be preserved",
            status=RunStatus.COMPLETED,
            task=task,
            blob_storage_used=True,
        )

        config = {
            "runs_data_cleanup_days": 30,
            "large_result_store": {
                "type": "azure",
                "container_name": "test-container",
                "connection_string": "DefaultEndpointsProtocol=https;AccountName=dummyname;AccountKey=dummykey",
            },
        }

        self.session.add(run)
        self.session.commit()

        cleanup.cleanup_runs_data(config, include_input=True)
        self.session.refresh(run)

        expected_calls = [call(self.uuid), call("input")]
        mock_delete_blob.assert_has_calls(expected_calls, any_order=False)

    def test_no_cleanup_recent_completed_run(self):
        # Ineligible: completed, but not old enough

        run = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=10),
            result=self.uuid,
            arguments="arguments",
            status=RunStatus.COMPLETED.value,
        )
        self.session.add(run)
        self.session.commit()

        cleanup.cleanup_runs_data({"runs_data_cleanup_days": 30}, include_args=True)
        self.session.refresh(run)
        self.assertEqual(run.result, self.uuid)
        self.assertEqual(run.arguments, "arguments")
        self.assertIsNone(run.cleanup_at)

    def test_no_cleanup_non_completed_run(self):
        # Ineligible: not COMPLETED, albeit old enough
        run = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=31),
            result=self.uuid,
            arguments="arguments",
            status=RunStatus.FAILED.value,  # Not COMPLETED, so ineligible
        )
        self.session.add(run)
        self.session.commit()

        cleanup.cleanup_runs_data({"runs_data_cleanup_days": 30}, include_args=True)
        self.session.refresh(run)
        self.assertEqual(run.result, self.uuid)
        self.assertEqual(run.arguments, "arguments")
        self.assertIsNone(run.cleanup_at)

    def test_cleanup_without_clearing_arguments(self):
        # Eligible: completed > 30 days ago
        run = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=40),
            result=self.uuid,
            arguments="arguments",
            status=RunStatus.COMPLETED.value,
        )
        self.session.add(run)
        self.session.commit()

        cleanup.cleanup_runs_data({"runs_data_cleanup_days": 30}, include_args=False)
        self.session.refresh(run)
        self.assertEqual(run.result, "")
        self.assertEqual(run.arguments, "arguments")
        self.assertIsNotNone(run.cleanup_at)


# Test cleanup_results()' handling of multiple runs
class TestCleanupRunsCount(unittest.TestCase):
    def setUp(self):
        Database().connect("sqlite://", allow_drop_all=True)
        self.session = DatabaseSessionManager.get_session()

    def tearDown(self):
        # clear_data() will clear session too
        Database().clear_data()
        Database().close()

    def create_runs(self):
        run0 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=31),
            result="result0",
            arguments="arguments0",
            status=RunStatus.COMPLETED.value,
        )
        run1 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=200),
            result="result1",
            arguments="arguments1",
            status=RunStatus.COMPLETED.value,
        )
        run2 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=10),
            result="result2",
            arguments="arguments2",
            status=RunStatus.COMPLETED.value,
        )
        run3 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=10),
            result="result3",
            arguments="arguments3",
            status=RunStatus.PENDING.value,
        )
        run4 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=31),
            result="result4",
            arguments="arguments4",
            status=RunStatus.FAILED.value,
        )
        run5 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=10),
            result="result5",
            arguments="arguments5",
            status=RunStatus.ACTIVE.value,
        )
        self.session.add_all([run0, run1, run2, run3, run4, run5])
        self.session.commit()

        return run0, run1, run2, run3, run4, run5

    def test_cleanup_runs_count(self):
        # Insert runs into db
        runs = self.create_runs()

        # clean up result and input from runs older than 30 days
        cleanup.cleanup_runs_data({"runs_data_cleanup_days": 30}, include_args=True)

        # db has been changed, refresh objects
        for run in runs:
            self.session.refresh(run)

        # Query the DB to get cleaned up and non-cleaned up runs
        cleaned_runs = self.session.scalars(
            select(Run).filter(Run.cleanup_at != None)
        ).all()
        remaining_runs = self.session.scalars(
            # ruff: noqa: E711
            select(Run).filter(Run.cleanup_at == None)
        ).all()

        # We expect only run0 and run1 to have been cleaned up
        self.assertEqual(len(cleaned_runs), 2)
        self.assertEqual(len(remaining_runs), 4)

        # Verify that cleaned runs have their result and arguments cleared, and
        # cleanup_at set
        for run in cleaned_runs:
            self.assertEqual(run.result, "")
            self.assertEqual(run.arguments, "")
            self.assertIsNotNone(run.cleanup_at)

        # Verify that runs that should not have been cleaned up keep their
        # result and arguments
        for i in range(2, 6):
            self.assertEqual(runs[i].result, f"result{i}")
            self.assertEqual(runs[i].arguments, f"arguments{i}")
