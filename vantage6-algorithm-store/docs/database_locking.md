# Database Locking Mechanism

## Overview

The algorithm store now includes a database-level locking mechanism to prevent race conditions when multiple processes try to modify the same tables simultaneously. This is particularly important during startup when multiple algorithm store instances might be running and trying to set up policies at the same time.

## Problem

Previously, when multiple algorithm store processes started simultaneously, they would all try to delete and recreate policies in the database at the same time, causing:

1. Race conditions in the database
2. Potential data corruption
3. `ObjectDeletedError` exceptions
4. Inconsistent policy states

## Solution

A `DatabaseLock` model has been implemented that provides:

1. **Database-level locking**: Uses a dedicated table to track active locks
2. **Process identification**: Each lock is associated with a unique process identifier (PID + hostname)
3. **Timeout mechanism**: Locks have configurable timeouts to prevent deadlocks
4. **Automatic cleanup**: Expired locks are automatically cleaned up
5. **Thread safety**: The locking mechanism is thread-safe

## Implementation Details

### DatabaseLock Model

The `DatabaseLock` model is defined in `vantage6/algorithm/store/model/base.py`:

```python
class DatabaseLock(Base):
    __tablename__ = 'database_lock'

    id = Column(Integer, primary_key=True)
    lock_name = Column(String, unique=True, nullable=False)
    process_id = Column(String, nullable=False)  # Process identifier (PID + hostname)
    acquired_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False)
```

### Key Methods

- `acquire_lock(lock_name, process_id, timeout_seconds=30)`: Attempts to acquire a lock
- `release_lock(lock_name, process_id)`: Releases a lock
- `_cleanup_expired_locks(session)`: Removes expired locks

### Usage in Policy Setup

The locking mechanism is used in the `setup_policies` method:

```python
def setup_policies(self, config: dict) -> None:
    # Generate a unique process identifier
    process_id = f"{os.getpid()}_{socket.gethostname()}"
    lock_name = "policy_setup"

    # Try to acquire the database lock for policy setup
    if not db.DatabaseLock.acquire_lock(lock_name, process_id, timeout_seconds=30):
        log.warning("Could not acquire policy setup lock, skipping policy setup")
        return

    try:
        # Perform policy setup operations...
        pass
    finally:
        # Always release the lock, even if an exception occurred
        db.DatabaseLock.release_lock(lock_name, process_id)
```

## Benefits

1. **Prevents race conditions**: Only one process can modify policies at a time
2. **Graceful degradation**: If a lock cannot be acquired, the process skips the operation rather than failing
3. **Automatic cleanup**: Expired locks are automatically removed
4. **Configurable timeouts**: Prevents indefinite waiting
5. **Process identification**: Easy to identify which process holds a lock

## Configuration

The locking mechanism has the following default settings:

- **Lock timeout**: 30 seconds (configurable)
- **Lock expiry**: 5 minutes (hardcoded)
- **Retry interval**: 100ms between retry attempts

## Testing

The locking mechanism is thoroughly tested in `tests_store/test_database_lock.py` with tests for:

- Basic lock acquisition and release
- Lock timeout behavior
- Expired lock cleanup
- Concurrent lock attempts
- Lock uniqueness

## Future Enhancements

The locking mechanism can be extended to other operations that require exclusive database access, such as:

- Database schema migrations
- Bulk data operations
- Configuration updates
- Any other critical database operations

## Migration

The `DatabaseLock` table will be automatically created when the algorithm store starts up, as it's part of the SQLAlchemy model definitions. No manual migration is required.
