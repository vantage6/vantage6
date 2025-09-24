import unittest

from datetime import datetime, timedelta, timezone
import uuid
from unittest.mock import patch, call

from vantage6.server.model.run import Run
from vantage6.server.model.base import Database, DatabaseSessionManager
from vantage6.server.controller import cleanup
from vantage6.common.task_status import TaskStatus
from vantage6.server.model import Task


class TestCleanupRunsIsolated(unittest.TestCase):
    def setUp(self):
        Database().connect("sqlite://", allow_drop_all=True)
        self.session = DatabaseSessionManager.get_session()

        self.uuid = str(uuid.uuid4())

    def tearDown(self):
        Database().clear_data()

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
            input="input",
            log="log should be preserved",
            status=TaskStatus.COMPLETED,
            task=task,
        )

        self.session.add(run)
        self.session.commit()

        cleanup.cleanup_runs_data({"runs_data_cleanup_days": 30}, include_input=True)
        self.session.refresh(run)
        self.assertEqual(run.result, "")
        self.assertEqual(run.input, "")
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
            status=TaskStatus.COMPLETED,
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
            input="input",
            status=TaskStatus.COMPLETED,
        )
        self.session.add(run)
        self.session.commit()

        cleanup.cleanup_runs_data({"runs_data_cleanup_days": 30}, include_input=True)
        self.session.refresh(run)
        self.assertEqual(run.result, self.uuid)
        self.assertEqual(run.input, "input")
        self.assertIsNone(run.cleanup_at)

    def test_no_cleanup_non_completed_run(self):
        # Ineligible: not COMPLETED, albeit old enough
        run = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=31),
            result=self.uuid,
            input="input",
            status=TaskStatus.FAILED,  # Not COMPLETED, so ineligible
        )
        self.session.add(run)
        self.session.commit()

        cleanup.cleanup_runs_data({"runs_data_cleanup_days": 30}, include_input=True)
        self.session.refresh(run)
        self.assertEqual(run.result, self.uuid)
        self.assertEqual(run.input, "input")
        self.assertIsNone(run.cleanup_at)

    def test_cleanup_without_clearing_input(self):
        # Eligible: completed > 30 days ago
        run = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=40),
            result=self.uuid,
            input="input",
            status=TaskStatus.COMPLETED,
        )
        self.session.add(run)
        self.session.commit()

        cleanup.cleanup_runs_data({"runs_data_cleanup_days": 30}, include_input=False)
        self.session.refresh(run)
        self.assertEqual(run.result, "")
        self.assertEqual(run.input, "input")
        self.assertIsNotNone(run.cleanup_at)


# Test cleanup_results()' handling of multiple runs
class TestCleanupRunsCount(unittest.TestCase):
    def setUp(self):
        Database().connect("sqlite://", allow_drop_all=True)
        self.session = DatabaseSessionManager.get_session()

    def tearDown(self):
        # clear_data() will clear session too
        Database().clear_data()

    def create_runs(self):
        run0 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=31),
            result="result0",
            input="input0",
            status=TaskStatus.COMPLETED,
        )
        run1 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=200),
            result="result1",
            input="input1",
            status=TaskStatus.COMPLETED,
        )
        run2 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=10),
            result="result2",
            input="input2",
            status=TaskStatus.COMPLETED,
        )
        run3 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=10),
            result="result3",
            input="input3",
            status=TaskStatus.PENDING,
        )
        run4 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=31),
            result="result4",
            input="input4",
            status=TaskStatus.FAILED,
        )
        run5 = Run(
            finished_at=datetime.now(timezone.utc) - timedelta(days=10),
            result="result5",
            input="input5",
            status=TaskStatus.ACTIVE,
        )
        self.session.add_all([run0, run1, run2, run3, run4, run5])
        self.session.commit()

        return run0, run1, run2, run3, run4, run5

    def test_cleanup_runs_count(self):

        # Insert runs into db
        runs = self.create_runs()

        # clean up result and input from runs older than 30 days
        cleanup.cleanup_runs_data({"runs_data_cleanup_days": 30}, include_input=True)

        # db has been changed, refresh objects
        for run in runs:
            self.session.refresh(run)

        # Query the DB to get cleaned up and non-cleaned up runs
        cleaned_runs = self.session.query(Run).filter(Run.cleanup_at != None).all()
        remaining_runs = self.session.query(Run).filter(Run.cleanup_at == None).all()

        # We expect only run0 and run1 to have been cleaned up
        self.assertEqual(len(cleaned_runs), 2)
        self.assertEqual(len(remaining_runs), 4)

        # Verify that cleaned runs have their result and input cleared, and
        # cleanup_at set
        for run in cleaned_runs:
            self.assertEqual(run.result, "")
            self.assertEqual(run.input, "")
            self.assertIsNotNone(run.cleanup_at)

        # Verify that runs that should not have been cleaned up keep their
        # result and input
        for i in range(2, 6):
            self.assertEqual(runs[i].result, f"result{i}")
            self.assertEqual(runs[i].input, f"input{i}")
