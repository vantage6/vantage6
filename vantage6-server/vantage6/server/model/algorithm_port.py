from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class AlgorithmPort(Base):
    """
    Table that describes which algorithms are reachable via which ports

    Each algorithm with a VPN connection can claim multiple ports via the
    Dockerfile ``EXPOSE`` and ``LABEL`` commands. These claims are saved in
    this table. Each algorithm container belongs to a single
    :class:`~vantage6.server.model.result.Result`.

    Attributes
    ----------
    port: int
        The port number that is claimed by the algorithm
    result_id: int
        The id of the :class:`~vantage6.server.model.result.Result` that this
        port belongs to
    label: str
        The label that is claimed by the algorithm
    result: :class:`~vantage6.server.model.result.Result`
        The :class:`~vantage6.server.model.result.Result` that this port
        belongs to
    """

    # fields
    port = Column(Integer)
    run_id = Column(Integer, ForeignKey("run.id"))
    label = Column(String)

    run = relationship("Run", back_populates="ports")
