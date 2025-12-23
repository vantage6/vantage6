from vantage6.common.enum import EnumBase


class AuthCredentials(EnumBase):
    KEYCLOAK_ADMIN_USER = ("keycloakAdminUser", "Keycloak admin username")
    KEYCLOAK_ADMIN_PASSWORD = ("keycloakAdminPassword", "Keycloak admin password")
    VANTAGE6_ADMIN_PASSWORD = ("vantage6AdminPassword", "Vantage6 admin password")

    def __new__(cls, value: str, description: str):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.description = description
        return obj
