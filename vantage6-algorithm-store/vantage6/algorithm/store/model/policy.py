from sqlalchemy import Column, String

from vantage6.algorithm.store.model.base import Base


class Policy(Base):
    """
    Table that describes the policies of this algorithm store.

    Attributes
    ----------
    key: str
        Key of the setting
    value: str
        Value of the setting
    """

    key = Column(String)
    value = Column(String)
