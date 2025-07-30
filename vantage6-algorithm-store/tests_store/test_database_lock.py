"""
Test the database locking mechanism to ensure it prevents race conditions
when multiple processes try to modify the same tables simultaneously.
"""

import unittest
import threading
import time
from unittest.mock import patch

from tests_store.base.unittest_base import TestResources
from vantage6.algorithm.store.model.base import DatabaseLock
from vantage6.algorithm.store.model.base import DatabaseSessionManager


class TestDatabaseLock(TestResources):
    """Test the database locking mechanism."""

    def test_acquire_and_release_lock(self):
        """Test that a lock can be acquired and released successfully."""
        process_id = "test_process_1"
        lock_name = "test_lock"

        # Test acquiring the lock
        self.assertTrue(DatabaseLock.acquire_lock(lock_name, process_id))

        # Verify the lock exists in the database
        session = DatabaseSessionManager.get_session()
        lock = session.query(DatabaseLock).filter_by(
            lock_name=lock_name,
            process_id=process_id
        ).first()
        self.assertIsNotNone(lock)

        # Test releasing the lock
        self.assertTrue(DatabaseLock.release_lock(lock_name, process_id))

        # Verify the lock was removed
        lock = session.query(DatabaseLock).filter_by(
            lock_name=lock_name,
            process_id=process_id
        ).first()
        self.assertIsNone(lock)

    def test_lock_timeout(self):
        """Test that lock acquisition times out when lock is held by another process."""
        process_id_1 = "test_process_1"
        process_id_2 = "test_process_2"
        lock_name = "test_lock_timeout"

        # Acquire lock with first process
        self.assertTrue(DatabaseLock.acquire_lock(lock_name, process_id_1))

        # Try to acquire the same lock with second process (should timeout)
        start_time = time.time()
        result = DatabaseLock.acquire_lock(lock_name, process_id_2, timeout_seconds=1)
        end_time = time.time()

        self.assertFalse(result)
        self.assertGreaterEqual(end_time - start_time, 1.0)  # Should have waited at least 1 second

        # Clean up
        DatabaseLock.release_lock(lock_name, process_id_1)

    def test_cleanup_expired_locks(self):
        """Test that expired locks are cleaned up automatically."""
        process_id = "test_process_expired"
        lock_name = "test_expired_lock"

        # Create a lock that expires in the past
        session = DatabaseSessionManager.get_session()
        expired_lock = DatabaseLock(
            lock_name=lock_name,
            process_id=process_id,
            acquired_at=time.time() - 3600,  # 1 hour ago
            expires_at=time.time() - 1800,   # 30 minutes ago
        )
        session.add(expired_lock)
        session.commit()

        # Verify the lock exists
        lock = session.query(DatabaseLock).filter_by(
            lock_name=lock_name,
            process_id=process_id
        ).first()
        self.assertIsNotNone(lock)

        # Trigger cleanup
        DatabaseLock._cleanup_expired_locks(session)

        # Verify the expired lock was removed
        lock = session.query(DatabaseLock).filter_by(
            lock_name=lock_name,
            process_id=process_id
        ).first()
        self.assertIsNone(lock)

    def test_concurrent_lock_attempts(self):
        """Test that only one thread can acquire the same lock at a time."""
        lock_name = "test_concurrent_lock"
        results = []

        def acquire_lock(process_id):
            """Helper function to acquire lock in a thread."""
            result = DatabaseLock.acquire_lock(lock_name, process_id, timeout_seconds=2)
            results.append((process_id, result))
            if result:
                time.sleep(0.1)  # Hold the lock briefly
                DatabaseLock.release_lock(lock_name, process_id)

        # Start multiple threads trying to acquire the same lock
        threads = []
        for i in range(3):
            thread = threading.Thread(target=acquire_lock, args=(f"process_{i}",))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Only one thread should have successfully acquired the lock
        successful_acquires = [r for r in results if r[1]]
        self.assertEqual(len(successful_acquires), 1)

        # Verify the lock was released
        session = DatabaseSessionManager.get_session()
        lock = session.query(DatabaseLock).filter_by(lock_name=lock_name).first()
        self.assertIsNone(lock)

    def test_lock_uniqueness(self):
        """Test that different lock names can be acquired simultaneously."""
        process_id = "test_process_unique"
        lock_name_1 = "test_unique_lock_1"
        lock_name_2 = "test_unique_lock_2"

        # Acquire two different locks
        self.assertTrue(DatabaseLock.acquire_lock(lock_name_1, process_id))
        self.assertTrue(DatabaseLock.acquire_lock(lock_name_2, process_id))

        # Verify both locks exist
        session = DatabaseSessionManager.get_session()
        lock1 = session.query(DatabaseLock).filter_by(lock_name=lock_name_1).first()
        lock2 = session.query(DatabaseLock).filter_by(lock_name=lock_name_2).first()
        self.assertIsNotNone(lock1)
        self.assertIsNotNone(lock2)

        # Clean up
        DatabaseLock.release_lock(lock_name_1, process_id)
        DatabaseLock.release_lock(lock_name_2, process_id)


if __name__ == "__main__":
    unittest.main()