"""
The task_depends_on table defines which tasks are depending on which other tasks. Each
line contains a task (ID) that depends_on another task (ID). Each task can depend on
multiple other tasks and each task can be depended on by multiple other tasks.
"""

from sqlalchemy import Column, Integer, ForeignKey, Table

from .base import Base


task_depends_on = Table(
    "task_depends_on",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("task.id"), primary_key=True),
    Column("depends_on_id", Integer, ForeignKey("task.id"), primary_key=True),
)
