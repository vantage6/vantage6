from vantage6.common.enum import EnumBase


class AuthCredentials(EnumBase):
    KEYCLOAK_ADMIN_USER = ("keycloakAdminUser", "Keycloak admin username")
    KEYCLOAK_ADMIN_PASSWORD = ("keycloakAdminPassword", "Keycloak admin password")
    VANTAGE6_ADMIN_PASSWORD = ("vantage6AdminPassword", "Vantage6 admin password")

    def __new__(cls, value: str, description: str):
        # EnumBase inherits from Enum; calling its __new__ triggers a guard in
        # the stdlib Enum that raises TypeError. Bypass Enum's __new__ and
        # use object.__new__ directly.
        obj = object.__new__(cls)
        obj._value_ = value
        obj.description = description
        return obj
