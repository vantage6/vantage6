"""
The Member table is used to link organizations and collaborations together.
Each line in the table represents that a certain organization is member
of a certain collaboration by storing the ids of the organization and
collaboration.

The StudyMember table is used to link organizations and studies together. A study
is a subset of organizations that form a collaboration. The table is structured in the
same way as the Member table.
"""

from sqlalchemy import Column, Integer, ForeignKey, Table

from vantage6.server.model.base import Base


Member = Table(
    "Member",
    Base.metadata,
    Column("organization_id", Integer, ForeignKey("organization.id")),
    Column("collaboration_id", Integer, ForeignKey("collaboration.id")),
)

StudyMember = Table(
    "StudyMember",
    Base.metadata,
    Column("organization_id", Integer, ForeignKey("organization.id")),
    Column("study_id", Integer, ForeignKey("study.id")),
)
