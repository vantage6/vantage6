from vantage6.common.enum import EnumBase


class KillInitiator(EnumBase):
    """
    Enum to store the initiator of a kill request
    """

    USER = "user"
    NODE_SHUTDOWN = "node_shutdown"
