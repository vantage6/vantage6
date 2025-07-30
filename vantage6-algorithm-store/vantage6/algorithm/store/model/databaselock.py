import time
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import Session
import logging

from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager

log = logging.getLogger(__name__)


class DatabaseLock(Base):
    """
    Table for managing database-level locks to prevent race conditions
    when multiple processes try to modify the same tables simultaneously.

    This is used to ensure only one process can perform certain operations
    like policy setup at a time.
    """

    __tablename__ = 'database_lock'

    id = Column(Integer, primary_key=True)
    lock_name = Column(String, unique=True, nullable=False)
    process_id = Column(String, nullable=False)  # Process identifier (PID + hostname)
    acquired_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    @classmethod
    def acquire_lock(cls, lock_name: str, process_id: str, timeout_seconds: int = 30) -> bool:
        """
        Try to acquire a database lock.

        Parameters
        ----------
        lock_name : str
            Name of the lock to acquire
        process_id : str
            Unique identifier for the current process
        timeout_seconds : int
            How long to wait for the lock to become available

        Returns
        -------
        bool
            True if lock was acquired, False otherwise
        """
        session = DatabaseSessionManager.get_session()

        # Clean up expired locks first
        cls._cleanup_expired_locks(session)

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            try:
                # Try to acquire the lock
                lock = cls(
                    lock_name=lock_name,
                    process_id=process_id,
                    acquired_at=datetime.utcnow(),
                    expires_at=datetime.utcnow() + timedelta(minutes=5)  # 5 minute expiry
                )
                session.add(lock)
                session.commit()
                log.info(
                    "Acquired database lock '%s' for process %s",
                    lock_name,
                    process_id
                )
                return True

            except Exception as e:
                session.rollback()
                log.debug("Failed to acquire lock '%s': %s", lock_name, e)
                time.sleep(0.1)  # Wait 100ms before retrying

        log.warning(
            "Failed to acquire database lock '%s' after %s seconds", lock_name,
            timeout_seconds)
        return False

    @classmethod
    def release_lock(cls, lock_name: str, process_id: str) -> bool:
        """
        Release a database lock.

        Parameters
        ----------
        lock_name : str
            Name of the lock to release
        process_id : str
            Process identifier that acquired the lock

        Returns
        -------
        bool
            True if lock was released, False otherwise
        """
        session = DatabaseSessionManager.get_session()

        try:
            lock = session.query(cls).filter_by(
                lock_name=lock_name,
                process_id=process_id
            ).first()

            if lock:
                session.delete(lock)
                session.commit()
                log.info(
                    "Released database lock '%s' for process %s", lock_name, process_id
                )
                return True
            else:
                log.warning("Lock '%s' not found for process %s", lock_name, process_id)
                return False

        except Exception as e:
            session.rollback()
            log.error("Error releasing lock '%s': %s", lock_name, e)
            return False

    @classmethod
    def _cleanup_expired_locks(cls, session: Session) -> None:
        """
        Remove expired locks from the database.

        Parameters
        ----------
        session : Session
            Database session
        """
        try:
            expired_locks = session.query(cls).filter(
                cls.expires_at < datetime.utcnow()
            ).all()

            for lock in expired_locks:
                session.delete(lock)

            if expired_locks:
                session.commit()
                log.info(
                    "Cleaned up %s expired database locks", len(expired_locks)
                )

        except Exception as e:
            session.rollback()
            log.error("Error cleaning up expired locks: %s", e)