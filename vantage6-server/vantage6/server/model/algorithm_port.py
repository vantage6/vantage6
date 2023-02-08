from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class AlgorithmPort(Base):
    """Table that describes which algorithms are reachable via which ports

    Each algorithm with a VPN connection can claim multiple ports via the
    Dockerfile EXPOSE and LABEL commands. These claims are saved in this table.
    """

    # fields
    port = Column(Integer)
    run_id = Column(Integer, ForeignKey("run.id"))
    label = Column(String)

    run = relationship("Run", back_populates="ports")
