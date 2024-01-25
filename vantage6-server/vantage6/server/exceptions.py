class VPNPortalAuthException(Exception):
    """Exception raised when the authentication with the VPN portal fails."""

    pass


class VPNConfigException(Exception):
    """
    Exception raised when the server admin provides invalid VPN configuration.
    """

    pass
